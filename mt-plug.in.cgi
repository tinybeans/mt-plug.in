#!/usr/bin/perl
# この mt-plug_in.cgi を mt-config.cgi と同じディレクトリに設置します。
use strict;
use warnings;
use utf8;
use Cwd 'getcwd';
use File::Spec;
use File::Path 'mkpath';
use File::Copy 'copy';
use Archive::Zip qw( :ERROR_CODES :CONSTANTS );
use Data::Dumper;

print_message('start');
# my $header = <<'EOD';
# <!DOCTYPE HTML>
# <html lang="ja-JP">
# <head>
# 	<meta charset="UTF-8">
# 	<title>Log - mt-plug.in</title>
# </head>
# <body>
# EOD

# ログを記録する変数
# my @log_msg = ($header);

# その場限りで使う汎用変数を宣言（他のスコープへ持ち越さないこと）
my ($file, $text, $config_yaml);

# zip ファイルが不要なら 0
my $use_zip = 1;
my $zip_dir = 'plugins_zip';
my $zip = Archive::Zip->new() if $use_zip;
my %zip_file_list;

# !mt-config.cgi から設定を取得する
open(FILE, '<', 'mt-config.cgi') or die qq(Can't open file "mt-config.cgi": $!);

my $mt_conf = {};
while (my $ line = <FILE>) {
    chomp $line;
    next if ($line =~ /^#/ or $line =~ /^\s*$/);
    $line =~ s/^\s*|\s*$//g;
    my @mt_confs = split /\s+/, $line;
    $mt_conf->{$mt_confs[0]} = $mt_confs[1];
}
close FILE;

# !確認用出力
# print '<h2>===== mt-config.cgi の値 =====</h2>';
# foreach my $item (keys %$mt_conf) {
#     print "$item : ". $mt_conf->{$item}. "<br />";
# }
# print '<h2>===== mt-config.cgi の値 =====</h2>';

# !mt-plug.in の設定
# !$conf
my $conf = {
    author_name    => "Tomohiro Okuwaki",
    author_link    => "",
    name           => "A My First Plugin",
    id             => "A_MyFirstPlugin",
    version        => "0.01",
    schema_version => "0.01",
    description    => "初めてのプラグイン",
    plugin_link    => "",
    doc_link       => "",

    # !config_settings : 環境変数
    config_settings => {
        UseMTAppjQuery => "1",
        AllowFileInclude => "0"
    },

    # !object_types : フィールドの拡張、独自オブジェクトの追加
    object_types => {
        # mt_entryテーブルの拡張
        entry => {
            free_str => {
                type => "string", # integer, smallint, float, string, text, boolean, datetime, timestamp, blob
                size => 32, # stringの場合のみ1~255
                label => "price"
                # not_null: 1
                # auto_increment: 1
                # revisioned: 1
            },
            free_text => {
                type => "text", # integer, smallint, float, string, text, boolean, datetime, timestamp, blob
                label => "自由テキスト"
                # not_null: 1
                # auto_increment: 1
                # revisioned: 1
            },
            free_int => {
                type => "integer", # integer, smallint, float, string, text, boolean, datetime, timestamp, blob
                label => "送料"
                # not_null: 1
                # auto_increment: 1
                # revisioned: 1
            }
        }
    },

    # !settings : プラグインごとに持つ固有の設定値
    settings => {
        my_first_plugis_setting_1 => {
            default => "デフォルト",
            scope => "blog"
        },
        my_first_plugis_setting_2 => {
            default => "",
            scope => "blog"
        },
        my_system_setting_1 => {
            default => "デフォルト",
            scope => "system"
        },
        my_system_setting_2 => {
            default => "",
            scope => "system"
        }
    },

    # !tags : 拡張テンプレートタグ
    tags => {
        block    => ['MyBlock'],
        function => ['MyFunc1:my_first_plugis_setting_1','MyFunc2:my_system_setting_1','MyFunc3'],
        modifier => ['sample']
    },

    # !static_files : mt-static/plugins にデータを置くか
    static_files => ['js','css','img'],

    # l10n : 翻訳
#     l10n => {
#         Tomohiro_Okuwaki => "奥脇 知宏",    
#     },

    # Path
#     plugin_files => "plugin_files",不要
};

# !必須項目の存在チェック
$conf->{id} =~ s/\W//g;
my @require = ('id', 'name', 'version');
foreach my $req (@require) {
    if (!defined $conf->{$req} or ($conf->{$req} eq '')) {
        error(qq("$req" is required.));
    }
}

# !変数の初期化
# !$yaml
# config_settings, object_types, callbacks, tags, settings, blog_config_template, system_config_template
my $yaml = {};

# 現在日時を取得
my ($sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst) = localtime();
$year += 1900;
$mon++;
my $today = "$year-$mon-$mday";

# !作成するプラグインのID
my $p_id = $conf->{id};
my $p_key = lc($p_id);
my $p_version = $conf->{version};
my $p_dirname = $p_id . '_' . $p_version;

# !パスの作成
my %dir = (mt => getcwd());
my $reg_mtdir = quotemeta($dir{mt});

# plugins
$dir{plugins_path} = (defined $mt_conf->{PluginPath}) ? $mt_conf->{PluginPath} : File::Spec->catdir($dir{mt}, 'plugins');
# plugins/MYPLUGIN_ID
$dir{p_root} = File::Spec->catdir($dir{plugins_path}, $p_id);
# plugins/MYPLUGIN_ID/php
$dir{p_php} = File::Spec->catdir($dir{p_root}, 'php');
# plugins/MYPLUGIN_ID/tmpl
$dir{p_tmpl} = File::Spec->catdir($dir{p_root}, 'tmpl');
# plugins/MYPLUGIN_ID/lib/MYPLUGIN_ID
$dir{p_lib} = File::Spec->catdir($dir{p_root}, 'lib', $p_id);
# plugins/MYPLUGIN_ID/lib/MYPLUGIN_ID/L10N
$dir{p_l10n} = File::Spec->catdir($dir{p_lib}, 'L10N');

# mt-static/plugins
$dir{static_path} = (defined $mt_conf->{StaticFilePath}) ? File::Spec->catdir($mt_conf->{StaticFilePath}, 'plugins')
    : File::Spec->catdir($dir{mt}, 'mt-static', 'plugins');

# mt-static/plugins/MYPLUGIN_ID
$dir{p_static} = File::Spec->catdir($dir{static_path}, $p_id);

# mt-plug.in自体の情報
my $plug_in_zip = File::Spec->catfile($dir{plugins_path}, 'mt-plug_in', 'zip');
my $plug_in_zip_crt = File::Spec->catfile($plug_in_zip, $p_dirname);

# これから作成するプラグイン固有のIDやパスはスカラー変数にセットする




# my $_plugin_root_dir_name = $p_id . "_" . $conf->{version};
# my $_path_plugin_files = $dir{plugins_path};
# # preg_replace( "/\W/", "", $_plugin_root_dir_name );
# # preg_replace( "/\W/", "", $_path_plugin_files );
# 
# # plugin_files/MYPLUGIN_ID_Ver
# my $_path = "$_path_plugin_files/$_plugin_root_dir_name";
# 
# # MYPLUGIN_ID_Ver/plugins/MYPLUGIN_ID
# my $_path_plugins = "$_path/plugins/$p_id";
# 
# 
# # MYPLUGIN_ID_Ver/mt-static/plugins/MYPLUGIN_ID
# my $_path_static  = "$_path/mt-static/$p_id";


# !処理開始

# !処理開始メッセージ
print "新しいプラグインを作成します...<br />";

# !plugin_files内に既にディレクトリが作成されていたら終了
# error(qq{"$dir{p_root}"が既に存在しています。}) if (-d $dir{p_root} or -d $dir{p_root});

# !L10Nディレクトリまで一気に作成
mkpath($dir{p_l10n});
make_zip_dir($dir{p_l10n});

# !L10N関連ファイルの作成
# !L10N.pm
$file = File::Spec->catfile($dir{p_lib}, 'L10N.pm');
$text = <<"EOS";
package ${p_id}::L10N;
use strict;
use base 'MT::Plugin::L10N';

1;
EOS
create_file($file, $text);

# !ja.pm
$file = File::Spec->catfile($dir{p_l10n}, 'ja.pm');
$text = <<"EOS";
package ${p_id}::L10N::ja;
use strict;
use base '${p_id}::L10N::en_us';
use vars qw ( %Lexicon );

%Lexicon = (
	'hoge' => 'ほげ',
);

1;
EOS
create_file($file, $text);

# !en_us.pm
$file = File::Spec->catfile($dir{p_l10n}, 'en_us.pm');
$text = <<"EOS";
package ${p_id}::L10N::en_us;
use strict;
use base '${p_id}::L10N';
use vars qw ( %Lexicon );

%Lexicon = ();

1;
EOS
create_file($file, $text);

my $callbacks;

# !環境変数 : config_settings
if (defined $conf->{config_settings}) {
    $config_yaml = "config_settings:\n";
    foreach my $key (keys %{$conf->{config_settings}}) {
        $config_yaml .= <<"EOS";
    $key:
        default: $conf->{config_settings}->{$key}
EOS
    }
    $yaml->{config_settings} = $config_yaml;
}

# !オブジェクトの拡張 : object_types
if (defined $conf->{object_types} and defined $conf->{schema_version}) {

    # !CMS.pm の作成
    my $cms_pm = File::Spec->catfile($dir{p_lib}, 'CMS.pm');
    $text = <<"EOS";
package ${p_id}::CMS;
use strict;

EOS
    create_file($cms_pm, $text);

    # config.yamlのcallbacks:の準備
    if (!defined $callbacks) {
        $callbacks = "callbacks:\n";
    }

    $config_yaml = <<"EOS";
schema_version: $conf->{schema_version}
object_types:
EOS

    # config.yamlのobject_types:の処理
    foreach my $class (keys %{$conf->{object_types}}) { # ex. $class = entry
        # config.yamlのcallbacks:の処理
        if ($class eq 'entry') {
            $callbacks .= "    MT::App::CMS::template_param.edit_entry: \$${p_key}::${p_id}::CMS::hdlr_edit_entry_param\n";
            $text = <<'EOS';
sub hdlr_edit_entry_param {
    my ($cb, $app, $param, $tmpl) = @_;
    my $pointer_id = 'keywords';
    my $pointer_node = $tmpl->getElementById($pointer_id);
    return unless $pointer_node;
    my $component = MT->component('___PLUGIN_ID___');
    my ($inner, $new_node);

EOS
            $text =~ s/___PLUGIN_ID___/$p_id/g;
            create_file($cms_pm, $text, 'append');
        }
        $config_yaml .= "    $class:\n";
        foreach my $field (keys %{$conf->{object_types}->{$class}}) { # ex. $field = free_int
            $config_yaml .= "        $field:\n";
            foreach my $option (keys %{$conf->{object_types}->{$class}->{$field}}) { # ex. $option = label
                my $value = $conf->{object_types}->{$class}->{$field}->{$option};
                $config_yaml .= "            $option: $value\n";
                if ($option eq 'type') {
                    if ($value eq 'integer') {
                        $text = <<'EOS';
    <input type="text" name="__ID__" id="__ID__" class="text num" value="<$mt:var name="__ID__" escape="html"$>" mt:watch-change="1" autocomplete="off" />
EOS
                    } elsif ($value eq 'text') {
                        $text = <<'EOS';
    <textarea name="__ID__" id="__ID__" class="text full low" cols="" rows="" mt:watch-change="1"><$mt:var name="__ID__" escape="html"$></textarea>
EOS
                    } else {
                        $text = <<'EOS';
    <input type="text" name="__ID__" id="__ID__" class="text full" value="<$mt:var name="__ID__" escape="html"$>" mt:watch-change="1" autocomplete="off" />
EOS
                    }
                    my $text_prev = <<'EOS';
    $inner =<<'MTML';
    <__trans_section component="__PLUGIN_ID__">
EOS
                    my $text_next = <<'EOS';
    </__trans_section>
MTML

    $new_node = $tmpl->createElement( 'app:setting', {
        id => '__ID__',
        class => 'sort-enabled',
        label => '__PLUGIN_ID_____ID__',
        label_class => 'top-label',
        show_label => 1,
    } );
    $new_node->innerHTML( $inner );
    $tmpl->insertAfter( $new_node, $pointer_node );

EOS
                    $text = $text_prev . $text . $text_next;
                    $text =~ s/__PLUGIN_ID__/$p_id/g;
                    $text =~ s/__ID__/$field/g;
                }
            }
            # CMS.pmへ追記
            if ($class eq 'entry') {
                create_file($cms_pm, $text, 'append');
            }
        }
        create_file($cms_pm, "}\n", 'append');
    }
    if (-f $cms_pm) {
        create_file($cms_pm, '1;', 'append');
    }
    $yaml->{object_types} = $config_yaml;
}

# !拡張テンプレートタグ : tags
if (defined $conf->{tags}) {
    $config_yaml = "tags:\n";

    # スタティック用
    my $perl_tags = <<"EOS";
package ${p_id}::Tags;
use strict;

EOS

    # ダイナミック・パブリッシング用のPHPディレクトリを作成
    mkpath($dir{p_php});
    make_zip_dir($dir{p_php});
    my $tags_pm = File::Spec->catfile($dir{p_lib}, 'Tags.pm');
    foreach my $tag_type (keys %{$conf->{tags}}) { # $tag_type = block or function or modifire  
        my $tag_list = $conf->{tags}->{$tag_type};
        my $prefix = ($tag_type eq 'modifier') ? 'fltr_': 'hdlr_';
        my ($perl_tag, $dynamic_text);
        $config_yaml .= "    $tag_type:\n";
        if ($tag_type eq 'block') {
            $perl_tag .= <<'EOS';
# Block Tags
sub __name__ {
    my ($ctx, $args, $cond) = @_;

    my $res = '';
    my $tokens = $ctx->stash('tokens');
    my $builder = $ctx->stash('builder');

#    foreach my $value (@values) {
        defined(my $out = $builder->build($ctx, $tokens, $cond))
            or return $ctx->error($builder->errstr);
        $res .= $out;
#    }
    return $res;
}

EOS
            $dynamic_text = <<'EOS';
<?php
function smarty_block_mt__name__ ($args, $content, &$ctx, &$repeat) {
    # ブログの取得
    $blog = $ctx->stash('blog');
    # エントリーの取得
    $entry = $ctx->stash('entry');
    # モディファイアの取得
    $hoge = $args['hoge'];
    return $content;
}
?>
EOS
        } elsif ($tag_type eq 'function') {
            $perl_tag .= <<'EOS';
# Function Tags
sub __name__ {
    my ($ctx, $args) = @_;
# do something
    return 'mt:__tagname__ is Function Tag.'; # || $ctx->error('blog');
}

EOS
            $dynamic_text = <<'EOS';
<?php
function smarty_function_mt__name__ ($args, &$ctx) {
    # ブログの取得
    $blog = $ctx->stash('blog');
    # エントリーの取得
    $entry = $ctx->stash('entry');
    # モディファイアの取得
    $hoge = $args['hoge'];
    return 'mt:__tagname__ is Function Tag.(Dynamic)';
}
?>
EOS
        } elsif ($tag_type eq 'modifier') {
            $perl_tag .= <<'EOS';
# Modifiers
sub __name__ {
    my ($str, $arg, $ctx) = @_;

    return '__tagname__ is Global Modifier.';
}

EOS
            $dynamic_text = <<'EOS';
<?php
function smarty_modifier___name__($text, $arg) {
    return '__tagname__ is Global Modifier.(Dynamic)';
}
?>
EOS
        }
        foreach my $tagname (@$tag_list) {
            my ($use_setting, $use_setting_scope);
            if ($tagname =~ /^([^:]+):([^:]+)$/) {
                $use_setting = $2;
                $tagname =~ s/^([^:]+):([^:]+)$/$1/;
                $use_setting_scope = $conf->{settings}->{$use_setting}->{scope};
                $use_setting_scope = ($use_setting_scope eq 'blog') ? q('blog:'.\$blog_id) : q('system');
            }
            my $lc_tagname = lc($tagname);
    
            # config.yamlに追記
            $config_yaml .= "        $tagname: \$${p_key}::${p_id}::Tags::${prefix}${lc_tagname}\n";

            # Tags.pmに追記するコンテンツを作成
            my $_pert_tag = $perl_tag;
            $_pert_tag =~ s/__tagname__/$tagname/g;
            $_pert_tag =~ s/__name__/$prefix.$lc_tagname/ge;
            if (defined $use_setting) {
                my $get_setting_code = <<"EOS";
    my \$p = MT->component('$p_id');
    my \$blog_id = \$ctx->stash('blog')->id;
    return \$p->get_config_value('$use_setting', $use_setting_scope) || '';
EOS
                $_pert_tag =~ s/# do something/$get_setting_code/;
            }
            $perl_tags .= $_pert_tag;

            # ダイナミック用のPHPファイルを作成
            $dynamic_text =~ s/__tagname__/$tagname/g;
            $dynamic_text =~ s/__name__/$prefix.$lc_tagname/ge;

            $file = ($tag_type eq 'modifier') ? "${tag_type}.${lc_tagname}.php": "${tag_type}.mt${lc_tagname}.php";
            $file = File::Spec->catfile($dir{p_php}, $file);
            create_file($file, $dynamic_text);
        }
    }
    # Tags.pmに追記
    $perl_tags .= '1;';
    create_file($tags_pm, $perl_tags, 'append');
    $yaml->{tags} = $config_yaml;
}

# !settings : プラグインの設定
if (defined $conf->{settings}) {
    mkpath($dir{p_tmpl});
    make_zip_dir($dir{p_tmpl});
    my $settings = {'blog' => '', 'system' => ''};

    $config_yaml = "settings:\n";

    foreach my $setting_name (keys %{$conf->{settings}}) {
        my $setting_value = $conf->{settings}->{$setting_name};
        my $scope = $setting_value->{scope};
        my $default = $setting_value->{default};

        # config.yamlに追記
        $config_yaml .= <<"EOS";
    $setting_name:
        scope: $scope
        default: $default
EOS

        # config_template の指定
        my $config_tmpl_type = $scope . '_config_template';
        if (!defined $yaml->{$config_tmpl_type}) {
            $yaml->{$config_tmpl_type} = "$config_tmpl_type: ${scope}_config.tmpl\n";
        }

        # プラグインの設定画面の作成
        my $config_tmpl = <<'EOS';
<mtapp:setting
    id="__ID__"
    label="__ID__"
    hint="__ID__"
    show_hint="1">

    <!-- input:text -->
    <input type="text" name="__ID__" id="__ID__" class="text" value="<mt:var name="__ID__" escape="html">" mt:watch-change="1" autocomplete="off" />

<mt:ignore>
    <!-- input:checkbox -->
    <input type="checkbox" name="__ID__" id="__ID__" value="1"<mt:if name="__UD__"> checked="checked"</mt:if> mt:watch-change="1" />
</mt:ignore>

<mt:ignore>
    <!-- input:radio -->
    <input type="radio" name="__ID__" id="__ID___1" value="foo"<mt:if name="__UD__" eq="foo"> checked="checked"</mt:if> mt:watch-change="1" />
    <input type="radio" name="__ID__" id="__ID___2" value="bar"<mt:if name="__UD__" eq="bar"> checked="checked"</mt:if> mt:watch-change="1" />
</mt:ignore>

<mt:ignore>
    <!-- textarea -->
    <textarea name="__ID__" id="__ID__" class="text high" mt:watch-change="1"><mt:var name="__ID__"></textarea>
</mt:ignore>

<mt:ignore>
    <!-- select -->
    <select name="__ID__" id="__ID__">
        <option value="foo"<mt:if name="__ID__" eq="foo"> selected="selected"</mt:if>>foo</option>
        <option value="bar"<mt:if name="__ID__" eq="bar"> selected="selected"</mt:if>>bar</option>
    </select>
</mt:ignore>

</mtapp:setting>

EOS
        $config_tmpl =~ s/__ID__/$setting_name/g;
        $file = File::Spec->catfile($dir{p_tmpl}, "${scope}_config.tmpl");
        create_file($file, $config_tmpl, 'append');
    }
    $yaml->{settings} = $config_yaml;
}

# !callbacks : コールバックの設定
if (defined $callbacks) {
    $yaml->{callbacks} = $callbacks;
}

print '<h2>config.yaml ----------</h2>';
foreach my $key (keys %$yaml) {
    print $yaml->{$key};
}
print '<h2>/config.yaml ----------</h2>';


# !config.yaml の作成
my $config_yaml_path = File::Spec->catfile($dir{p_root}, 'config.yaml');

$config_yaml = <<"EOS";
# $conf->{name}
#
# Release $conf->{version} ($today)
#
# Copyright (c) $conf->{author_name}. / Powered by mt-plug.in
EOS

$config_yaml .= <<"EOS";
name: $conf->{name}
id: $p_id
key: $p_key
version: $conf->{version}
EOS

$config_yaml .= qq(author_name: <__trans phrase="$conf->{author_name}">\n) if (isset_config('author_name'));
$config_yaml .= qq(author_link: $conf->{author_link}\n) if (isset_config('author_link'));
$config_yaml .= qq(description: <__trans phrase="$conf->{description}">\n) if (isset_config('description'));
$config_yaml .= qq(plugin_link: $conf->{plugin_link}\n) if (isset_config('plugin_link'));
$config_yaml .= qq(doc_link: $conf->{doc_link}\n) if (isset_config('doc_link'));
$config_yaml .= qq(l10n_class: ${p_id}::L10N\n);
$config_yaml .= $yaml->{system_config_template} if (defined $yaml->{system_config_template});
$config_yaml .= $yaml->{blog_config_template} if (defined $yaml->{blog_config_template});

#init_request: >
#    sub {
#        my \$app = MT->instance;
#        my \$ua = \$app->get_header( 'User-Agent' );
#        unless ( ref \$app eq 'MT::App::CMS' ) {
#            if ( \$ua =~ /\ADoCoMo\/2\.0 /i ) {
#                \$app->{ response_content_type } = 'application/xhtml+xml';
#            }
#        }
#    }

$config_yaml .= $yaml->{config_settings} if (defined $yaml->{config_settings});
$config_yaml .= $yaml->{object_types} if (defined $yaml->{object_types});

#applications:
#    cms:
#        menus:
#            tools:clear_cache:
#                label: Flush Dynamic Cache
#                order: 20000
#                mode: flush_dynamic_cache
#                condition: \$dynamicmtml::DynamicMTML::CMS::_dynamic_permission
#        methods:
#            install_dynamic_mtml: \$dynamicmtml::DynamicMTML::CMS::_install_dynamic_mtml
#            flush_dynamic_cache: \$dynamicmtml::DynamicMTML::CMS::_flush_dynamic_cache

$config_yaml .= $yaml->{tags} if (defined $yaml->{tags});
$config_yaml .= $yaml->{settings} if (defined $yaml->{settings});
$config_yaml .= $yaml->{callbacks} if (defined $yaml->{callbacks});

create_file($config_yaml_path, $config_yaml);

# !mt-static ディレクトリの作成
if (defined $conf->{static_files}) {
    mkpath($dir{p_static});
    make_zip_dir($dir{p_static});
    if (scalar(@{$conf->{static_files}}) > 0) {
        foreach my $dir (@{$conf->{static_files}}) {
            $dir = File::Spec->catdir($dir{p_static}, $dir);
            mkdir($dir) or error(qq(Can't make "$dir": $!));
            make_zip_dir($dir);
            $zip_file_list{$dir} = 1 if ($use_zip);
        }
    }
}

# !zipファイルの作成
if ($use_zip) {
    foreach my $f (keys %zip_file_list) {
        $zip->addFile($f);
    }
    my $zip_file = File::Spec->catfile($zip_dir, $p_dirname . '.zip');
    if ($zip->writeToFileNamed($zip_file) == AZ_OK) {
        print qq("$zip_file" is successfully saved.\n);
    } else {
        error(qq("$zip_file" save error: $!\n));
    }
}

print_message('end');
exit();

# !subroutines
sub create_file {
    my ($file, $content, $append) = @_;
    if (-e $file and !defined $append) {
        error("$file は、すでに存在します。");
    } elsif (defined $append) {
        open(FILE, ">>", $file) or error(qq(Can't open "$file" by ">>"mode: $!));
        print FILE $content if (defined $content);
        close FILE;
    } else {
        open(FILE, ">", $file) or error(qq(Can't open "$file" by ">"mode: $!));
        print FILE $content if (defined $content);
        close FILE;
    }
    if ($use_zip) {
        my $file_zip = $file;
        $file_zip =~ s/($reg_mtdir)(.+)/$2/g;
        $file_zip =~ s!^/|/$!!g;
        $file_zip = File::Spec->catfile($zip_dir, $p_dirname, $file_zip);
        if (defined $append) {
            open(FILE, ">>", $file_zip) or error(qq(Can't open "$file_zip" by ">>"mode: $!));
            print FILE $content if (defined $content);
            close FILE;
        } else {
            open(FILE, ">", $file_zip) or error(qq(Can't open "$file_zip" by ">"mode: $!));
            print FILE $content if (defined $content);
            close FILE;
        }
        $zip_file_list{$file_zip} = 1;
    }
}

sub make_zip_dir {
    my ($path) = @_;
    return unless $use_zip;
    $path =~ s/($reg_mtdir)(.+)/File::Spec->catdir($zip_dir, $p_dirname, $2)/ge;
    mkpath($path);
}

sub setting_yaml {
    my ($key, $value, $res, $force) = @_;
    if (defined $conf->{$key} and $conf->{$key} ne '') {
        if (defined $value) {
            push @$res, "$key: $value";
        } else {
            push @$res, "$key: $conf->{$key}";
        }
    } elsif (defined $force) {
        push @$res, "$key: $value";
    }
    return $res;
}

sub isset_config {
    my $key = shift;
    return (defined $conf->{$key} and $conf->{$key} ne '');
}

sub format_W {
    my $text = shift;
    $text =~ s/\W//g;
    return $text;
}

sub print_message {
    my $type = shift;
    if ($type eq 'start') {
        print "Content-type: text/html\n\n";
        print '<pre style="font-size:1.2em;">';
    } elsif ($type eq 'end') {
        print '<h2>プラグインが作成されました。</h2>';
    }
}
sub error {
    my ($text) = shift;
    print qq(<span style="color:red;">Error: $text</span>);
    exit();
}

=POD

!config.yaml の作成 ########################################

$cnf_yaml .= 
<<<CONFIG_YAML
#callbacks:
#    {$conf->{id"]}: \${$conf->{id"]}::{$conf->{id"]}::Comment::ext_filter
#    MT::App::CMS::template_source.list_template: $dynamicmtml::DynamicMTML::Plugin::_list_template_source
#    MT::App::CMS::template_param.list_template: $dynamicmtml::DynamicMTML::Plugin::_list_template_param
#    MT::App::CMS::template_param.cfg_prefs: $dynamicmtml::DynamicMTML::Plugin::_cfg_prefs_param
#    MT::App::CMS::template_source.cfg_prefs: $dynamicmtml::DynamicMTML::Plugin::_cfg_prefs_source
#    MT::App::CMS::template_source.footer: $dynamicmtml::DynamicMTML::Plugin::_footer_source
#    MT::App::CMS::template_param.edit_template: $dynamicmtml::DynamicMTML::Plugin::_edit_template_param
#    build_file: $dynamicmtml::DynamicMTML::Plugin::_build_file
#    build_page: $dynamicmtml::DynamicMTML::Plugin::_build_page
#    build_file_filter: $dynamicmtml::DynamicMTML::Plugin::_build_file_filter
#    build_dynamic: $dynamicmtml::DynamicMTML::Plugin::_build_dynamic
#    cms_post_save.blog:
#        - handler: $dynamicmtml::DynamicMTML::Plugin::_post_save_blog
#          priority: 10
#        - handler: $dynamicmtml::DynamicMTML::Plugin::_disable_dynamicmtml
#          priority: 1
#    cms_post_save.template: $dynamicmtml::DynamicMTML::Plugin::_post_save_template
#    MT::App::CMS::template_param.view_log: $dynamicmtml::DynamicMTML::Plugin::_view_log
#    MT::App::CMS::template_param: $dynamicmtml::DynamicMTML::Plugin::_cb_tp

CONFIG_YAML;
*/


/* !zip ファイルの出力 ######################################## */

# ディレクトリを移動
chdir( $_path_plugin_files );


# zipファイルのダウンロード
if ( file_exists( "{$_path_plugin_files}/{$zipfile}" )) {
    do_log( "{$zipfile}を作成しました！" );
    echo '<p><a href="../' . preg_replace( "/\W/", "", $conf->{plugin_files"] ) . '/' . $zipfile . '">' . $zipfile . ' (size: ' .filesize( $zipfile ) . ' bytes)</a></p>';
} else {
    do_log( "{$zipfile}の作成に失敗しました。", "error" );
}


=cat
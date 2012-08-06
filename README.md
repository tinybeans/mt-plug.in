mt-plug.in.cgi について

## mt-plug.in とは

mt-plug.in は、Movable type のプラグインのひな形を簡単に作ることができるCGIです。

## 使い方

1. mt-plug.in.cgi を Movable Type のインストールディレクトリ（つまり mt-config.cgi があるディレクトリ。以下「MT_DIR」と言います）に設置します。
1. mt-plug.in.cgi に 755 など実行権限を与えます。
1. mt-plug.in.cgi の「設定ここから」〜「設定ここまで」の間の設定を編集します。
1. ブラウザで mt-plug.in.cgi にアクセスすればプラグインのひな形が Movable Type にインストールされます。

## その他説明

### 設定方法

設定方法は mt-plug.in.cgi の該当箇所にコメントしてありますので、そちらをご覧ください。
コツとしては不要なモノは行ごとに丸ごとコメントアウトした方が良いかもしれません。

### Internal Server Error が表示される

mt-plug.in.cgi にアクセスしたときに「Internal Server Error」が表示された場合は編集した設定に間違いがある可能性が高いです。

できれば、アクセスする前にコマンドラインで Perl の文法チェックをしておいた方がよいでしょう。

```
perl -c /ファイルまでのぱす（それぞれの環境によって違います)/mt-plug.in.cgi
```


### 作成されるディレクトリ・ファイルについて

mt-plug.in.cgi にアクセスすると以下のディレクトリにプラグインのディレクトリが作成されます。

- MT_DIR/plugins
- MT_DIR/mt-static/plugins（設定次第）

また、MT_DIR に plugins_zip というディレクトリが作成され、その中に、「プラグインID_バージョン」という名前のディレクトリが作られます。

そのディレクトリには、plugins, mt-static/plugins に作成されるファイルがまとめて作成されます。それと同時に、このディレクトリの zip ファイルも生成されます。

```
MT_DIR
    └── plugins_zip
        └── MyFirstPlugin_0.01
        │   ├── plugins/MyFirstPlugin …
        │   └── mtstatic/plugins/MyFirstPlugin …
        └── MyFirstPlugin_0.01.zip
```

なお、zipファイルには mt-static/plugins ディレクトリ以下に作成されるディレクトリは入りません。

## 今後について

もう少し簡単に色々なプラグインができるようにしたいと思っています（2012年8月6日、tinybeans談）

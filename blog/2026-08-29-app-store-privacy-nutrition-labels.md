---
title: "App Store Connect「Appのプライバシー」設定と用語解説（AdMob・Firebase・ATT対応）"
date: "2026-08-29"
description: "iOSアプリをApp Storeに初リリースする際に必須となる「Appのプライバシー（データ収集項目の回答）」について、各項目の意味、一次情報、判定基準、AdMobやFirebase導入時の正解設定、および後からの変更可否のまとめ。"
tags: ["iOS", "App Store Connect", "Privacy", "AdMob", "Firebase", "個人開発"]
---

# App Store Connect「Appのプライバシー」設定と用語解説（AdMob・Firebase・ATT対応）

## 1. 概要・要約（TL;DR）

iOS アプリを App Store Connect で審査提出する際、**「Appのプライバシー（App Privacy Details / 通称：プライバシー栄養表示ラベル）」** の回答が必須となる。

会員登録・ログイン機能を持たず、**Google AdMob、Firebase Analytics、Firebase Crashlytics** を導入している一般的な個人開発アプリ（Kotlin Multiplatform / iOS）における設定方針は以下の通り。

```mermaid
graph TD
    A["アプリでデータを収集しているか？"] -->|Yes| B["収集データ: ID / 利用状況 / 診断"]
    B --> C["【設問1】ユーザの個人情報に関連付けられるか？"]
    C -->|アカウントや氏名/メアドと紐付かない| D["❌ いいえ (Not Linked to User)"]
    B --> E["【設問2】トラッキング目的に使用されるか？"]
    E -->|他社アプリ/サイトを跨いで行動追跡 (AdMob/IDFA)| F["⭕ はい (Used for Tracking)"]
    E -->|アプリ内での分析・品質改善のみ| G["❌ いいえ"]
```

### 結論サマリー

| データカテゴリ | 収集項目 | 該当SDK | 使用目的 | ユーザへのリンク<br>(個人情報への関連付け) | トラッキング目的 |
| :--- | :--- | :--- | :--- | :---: | :---: |
| **ID** | **ユーザID** | Firebase / AdMob | アナリティクス<br>サードパーティ広告 | ❌ **いいえ** | ⭕ **はい** |
| **ID** | **デバイスID** (IDFA等) | Google AdMob | アナリティクス<br>サードパーティ広告 | ❌ **いいえ** | ⭕ **はい** |
| **使用状況データ** | **製品の操作** | Firebase Analytics | アナリティクス | ❌ **いいえ** | ❌ **いいえ** |
| **診断** | **クラッシュデータ** | Firebase Crashlytics | アナリティクス<br>Appの機能 | ❌ **いいえ** | ❌ **いいえ** |
| **診断** | **パフォーマンスデータ** | Firebase Crashlytics | アナリティクス<br>Appの機能 | ❌ **いいえ** | ❌ **いいえ** |

---

## 2. 対象環境・構成

- **プラットフォーム**: iOS 16.0+
- **開発フレームワーク**: Kotlin Multiplatform (KMP) / Compose Multiplatform
- **広告SDK**: Google Mobile Ads SDK (Swift Package Manager 経由)
- **分析・診断SDK**: Firebase iOS SDK v11.15.0 (`FirebaseAnalytics`, `FirebaseCrashlytics`)
- **許諾ダイアログ**: App Tracking Transparency (ATT) 実装済み

---

## 3. 各項目の詳細と判定基準

### ① 「ユーザの個人情報に関連付けられますか？」（Linked to the User）
* **Apple の定義**: 収集したデータが、ユーザーの身元（実名、メールアドレス、電話番号、会員アカウント、物理的住所など）に関連付けられているかどうか。
* **判定**: **❌「いいえ」**
* **理由**: 本アプリには会員登録やログイン機能が存在せず、個人情報を一切収集・保持していない。Firebase や AdMob が内部的に発行するランダムな識別子は「匿名データ」扱いとなるため。

### ② 「トラッキング目的に使用されますか？」（Used for Tracking）
* **Apple の定義**: アプリから収集した特定のユーザーまたはデバイスに関するデータを、ターゲティング広告や広告測定のためにサードパーティデータとリンクすること、またはデータブローカーと共有すること。
* **判定**:
  * **ユーザID / デバイスID (IDFA)**: **⭕「はい」**（AdMob によるパーソナライズ広告配信・ATT ダイアログ対象のため）
  * **使用状況データ / 診断データ**: **❌「いいえ」**（自アプリの品質向上・分析目的のみのため）

### ③ 「使用目的」の分類
* **サードパーティ広告 (Third-Party Advertising)**: AdMob などの広告表示、クリック・表示計測。
* **アナリティクス (Analytics)**: Firebase Analytics 等による画面遷移や利用頻度・滞在時間の傾向分析。
* **Appの機能 (App Functionality)**: Crashlytics 等によるアプリのクラッシュログ収集、バグ原因特定・品質改善。

---

## 4. よくある疑問・運用ルール

### Q1. 「公開」ボタンを押すとアプリ本体もリリースされてしまうか？
* **A. リリースされない。**
* 「Appのプライバシー」右上の青い「公開」ボタンは、あくまで**「プライバシー回答の確定・保存（有効化）」**を行うボタン。
* アプリ本体の審査提出・公開は、バージョン詳細画面（例:「1.0 提出準備中」）から別途実行する。

### Q2. 設定内容は後から変更できるか？
* **A. いつでも自由に変更・再公開可能。**
* 新しいビルドの提出時だけでなく、いつでもこの画面から編集・保存して即座に App Store ページに反映できる。
* **将来変更が必要になるケース**:
  1. **ユーザー管理（会員登録・ログイン機能）を追加した時**: 「メールアドレス」「氏名」等の項目を追加し、個人情報への紐付けを「はい」に変更する。
  2. **SDK の追加・削除**: 新規ツール導入時は収集データに応じた項目を追加し、広告削除時はトラッキング項目を削除する。

---

## 5. 一次情報・公式リファレンス

1. **Apple Developer Documentation（Appのプライバシー詳細）**
   - [App Store での App のプライバシー詳細](https://developer.apple.com/jp/app-store/app-privacy-details/)
     - データタイプ、目的、データとユーザーの関連付け、トラッキングの公式定義。
   - [User Privacy and Data Use (トラッキングとATTの定義)](https://developer.apple.com/app-store/user-privacy-and-data-use/)

2. **Google Developers 公式ドキュメント**
   - [Google Mobile Ads SDK: App Store のデータ開示要件への対応](https://developers.google.com/admob/ios/data-disclosure?hl=ja)
     - AdMob SDK が収集するデータ（デバイスID、製品の操作、診断データなど）と App Store Connect での回答例。
   - [Firebase: Apple の App Store データ開示への対応](https://firebase.google.com/docs/ios/app-store-data-disclosure?hl=ja)
     - Analytics および Crashlytics のデータ収集項目と目的の公式マッピング。

---

## 6. 未解決事項・今後の課題

- **Privacy Manifest (`PrivacyInfo.xcprivacy`) の最新要件フォロー**:
  - Apple は 2024 年春以降、サードパーティ SDK のプライバシーマニフェスト対応を義務化している。AdMob や Firebase SDK は最新 SPM パッケージ内にマニフェストを内包しているが、将来 SDK をアップデートした際にもマニフェストの差分と署名状態を確認する。

---

## 7. 補足：AIアシスタントとのやり取り（背景ログ）

### ユーザーからの質問
> 2.1 Appのプライバシー（データ収集項目の回答）の設定中です。
> 「このアプリから収集されるユーザIDはユーザの個人情報に関連付けられますか？」はどっちを選んだら良い？
> 今設定した内容で「公開」ボタンを押しても良い？ 各項目の意味や後から変更できるかも記録しておきたい。

### AIの回答要点
- 会員登録や個人情報を持たないアプリでは「個人情報への関連付け＝いいえ」「IDのトラッキング＝はい」が正しい設定であることを図解。
- 「公開」ボタンはプライバシー設定の確定保存であり、アプリ本体が即時公開されるわけではない点を解説。

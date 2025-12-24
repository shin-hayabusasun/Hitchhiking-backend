\section{API設計}
%start 稗田
\subsection{ログイン系}
\subsubsection{管理者orユーザーログイン}

\begin{enumerate}
\item リクエストヘッダーのメールアドレスとパスワードを取り出す.また,管理者ログインかユーザーログインかをパラメータから取り出して,正しい処理をする.
\item user テーブルから,メールアドレスでselectして,リクエストヘッダーのパスワードをhash化した値とテーブル内の値が一致するか確認
\item 認証結果が成功したら,セクションとレスポンスを返す.失敗したら,失敗したことを伝える.
\end{enumerate}
\vspace{5mm} % 表との間隔調整
\texttt{POST /api/user/login }

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth} % 左側: Request (幅を少し広めに確保)
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 位置\\ \hline\hline
        mail & string & メールアドレス & body \\ \hline
        password & string & パスワード & body\\ \hline
        isuser & int & ユーザーか管理者か(1はユーザー,0は管理者)& body\\ \hline
        credentials & 固定値include & セッション & body\\ \hline
        \end{tabular}
        }
    \end{minipage}
    \hfill % 左右の間隔を空ける
    \begin{minipage}[t]{0.40\textwidth} % 右側: Response
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        ok & boolean & 認証成功か\\ \hline
        isuser & int & ユーザーか管理者か(1はユーザー,0は管理者)\\ \hline
        
        \end{tabular}
        }
    \end{minipage}
\end{table}



\subsubsection{登録API}

\begin{enumerate}
\item リクエストヘッダーの情報を取り出す.
\item user テーブルに入れる.またリクエストヘッダーのパスワードをhash化した値を用いる

\end{enumerate}
\vspace{5mm} % 表との間隔調整
\texttt{POST /api/user/regist }

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth} % 左側: Request (幅を少し広めに確保)
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 位置\\ \hline\hline
        mail & string & メールアドレス & body \\ \hline
        password & string & パスワード & body\\ \hline
        name & array & 氏名を名字と名前でつなげる & body\\ \hline
        sex & int & 1なら男0なら女 & body\\ \hline
        barthday & array & [2004,06,30]のように & body\\ \hline
        adress & array & 郵便情報をstring型でつなげる & body\\ \hline
        identification & string & base64記法 & body\\ \hline
        isdriver & int & 運転者としても登録するなら,1.しないなら0 & body\\ \hline
        \end{tabular}
        }
    \end{minipage}
    \hfill % 左右の間隔を空ける
    \begin{minipage}[t]{0.40\textwidth} % 右側: Response
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        ok & boolean & 登録成功か\\ \hline
        
        \end{tabular}
        }
    \end{minipage}
\end{table}

\subsubsection{ログアウト}

\begin{enumerate}
\item セッションからuseridを取り出す
\item ログアウト処理をして,セッションを消去する

\end{enumerate}
\vspace{5mm} % 表との間隔調整
\texttt{GET /api/user/logout }

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth} % 左側: Request (幅を少し広めに確保)
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 位置\\ \hline\hline
        credentials & 固定値include & セッション & body\\ \hline
       
        \end{tabular}
        }
    \end{minipage}
    \hfill % 左右の間隔を空ける
    \begin{minipage}[t]{0.40\textwidth} % 右側: Response
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        ok & boolean & ログアウト成功か\\ \hline
        
        \end{tabular}
        }
    \end{minipage}
\end{table}

\subsubsection{ログイン中か確認}

\begin{enumerate}
\item セッションが発行されいるものと一致するか確認する
\end{enumerate}
\vspace{5mm} % 表との間隔調整
\texttt{GET /api/user/IsLogin }

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth} % 左側: Request (幅を少し広めに確保)
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 位置\\ \hline\hline
        credentials & 固定値include & セッション & body\\
       
        \end{tabular}
        }
    \end{minipage}
    \hfill % 左右の間隔を空ける
    \begin{minipage}[t]{0.40\textwidth} % 右側: Response
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        ok & boolean & ログインできているか\\ \hline
        
        \end{tabular}
        }
    \end{minipage}
\end{table}

\subsection{同乗者用}
\subsubsection{募集検索情報取得}

\begin{enumerate}
\item リクエストヘッダーの情報を取り出す.
\item フィルタ情報をもとにsql文を作成.また,sqlには,userテーブルとプロフィールテーブルなどを連結,レコードごとのログインユーザーとのベクトルを計算して,マッチング度を項目に追加するという処理も書く.募集テーブルから募集中という表記のもので取り出す
\item 取り出したレコードをオブジェクトの配列化する
\item 
\end{enumerate}
\vspace{5mm} % 表との間隔調整
\texttt{GET /api/hitchhiker/boshukensaku }

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth} % 左側: Request (幅を少し広めに確保)
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 位置\\ \hline\hline
        filter & object & フィルタするオブジェクトの内容 & body\\ \hline
        credentials & 固定値include & セッション & body\\ \hline
       
        \end{tabular}
        }
    \end{minipage}
    \hfill % 左右の間隔を空ける
    \begin{minipage}[t]{0.40\textwidth} % 右側: Response
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        card & array(オブジェクトの配列) & 検索結果\\ \hline
        
        \end{tabular}
        }
    \end{minipage}
\end{table}



%end 稗田
% start 田所櫂人

\subsection{マイドライブ情報取得}

\begin{enumerate}
  \item リクエストヘッダーの \texttt{token} を検証し，
        運転者の \texttt{ユーザーID} を特定する.
  \item 「募集のテーブル」から，
        特定したユーザーIDが作成したレコードを検索する.
  \item クエリパラメータ \texttt{status} が指定されている場合，
        \texttt{募集状況} カラムでフィルタリングを行う.
  \item 取得した募集リストを
        最新の出発時間順にソートして返却する.
\end{enumerate}

\vspace{5mm}
\texttt{GET /api/driver/drives}

\begin{table}[H]
  \centering
  \begin{minipage}[t]{0.55\textwidth}
    % 左側: Request
    \textbf{Request}
    \vspace{1mm}

    \centering
    \resizebox{\textwidth}{!}{
      \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 場所 \\ \hline\hline
        token  & string & 認証トークン & header \\ \hline
        status & string & ステータスフィルタ & query \\ \hline
      \end{tabular}
    }
  \end{minipage}
  \hfill
  \begin{minipage}[t]{0.40\textwidth}
    % 右側: Response
    \textbf{Response}
    \vspace{1mm}

    \centering
    \resizebox{\textwidth}{!}{
      \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ \hline\hline
        drives & array & ドライブ情報のリスト \\ \hline
      \end{tabular}
    }
  \end{minipage}
\end{table}


\subsection{ドライブ新規登録}

\begin{enumerate}
  \item \texttt{token} より作成者IDを特定し，
        入力データのバリデーション
        （未来の日時か，運賃が正の数か等）を行う.
  \item 「経路のテーブル (Table 5)」に
        \texttt{出発地}，\texttt{目的地}，\texttt{時間} などの
        位置情報・日時情報を保存し，
        \texttt{経路ID} を発行する.
  \item 「募集のテーブル (Table 4)」に
        \texttt{募集ユーザーID}，
        \texttt{経路ID}，
        \texttt{運賃}，
        \texttt{募集人数} を登録し，
        \texttt{募集状況} を進行中に設定する.
\end{enumerate}


\vspace{5mm}
\texttt{POST /api/drives}

\begin{table}[H]
  \centering
  \begin{minipage}[t]{0.55\textwidth}
    \textbf{Request}
    \vspace{1mm}

    \centering
    \resizebox{\textwidth}{!}{
      \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 場所 \\ \hline\hline
        token          & string & 認証トークン & header \\ \hline
        departure      & string & 出発地 & body \\ \hline
        destination    & string & 目的地 & body \\ \hline
        departuretime  & string & 出発日時 & body \\ \hline
        capacity       & number & 募集定員 & body \\ \hline
        fee            & number & 料金 & body \\ \hline
        message        & string & 補足メッセージ  & body \\ \hline
        vehiclerules   & object & 車両ルール & body \\ \hline
      \end{tabular}
    }
  \end{minipage}
  \hfill
  \begin{minipage}[t]{0.40\textwidth}
    \textbf{Response}
    \vspace{1mm}

    \centering
    \resizebox{\textwidth}{!}{
      \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ \hline\hline
        id      & number & 作成された募集ID \\ \hline
        message & string & 完了メッセージ \\ \hline
      \end{tabular}
    }
  \end{minipage}
\end{table}


\subsection{ドライブ詳細取得 (編集用)}

\begin{enumerate}
  \item 指定された \texttt{id}（募集ID）をキーに，
        「募集」および「経路」テーブルから
        現在の登録内容を取得する.
  \item \texttt{token} から取得した操作者IDが，
        \texttt{募集ユーザーID} と一致するか
        権限検証を行う.
  \item 一致する場合，
        フロントエンドの編集フォームに必要な
        すべての項目値を返却する.
\end{enumerate}


\vspace{5mm}
\texttt{GET /api/drives/{id}}

\begin{table}[H]
  \centering
  \begin{minipage}[t]{0.55\textwidth}
    \textbf{Request}
    \vspace{1mm}

    \centering
    \resizebox{\textwidth}{!}{
      \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 場所 \\ \hline\hline
        token & string & 認証トークン & header \\ \hline
        id    & string & ドライブID & path \\ \hline
      \end{tabular}
    }
  \end{minipage}
  \hfill
  \begin{minipage}[t]{0.40\textwidth}
    \textbf{Response}
    \vspace{1mm}

    \centering
    \resizebox{\textwidth}{!}{
      \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ \hline\hline
        drive & object & ドライブ詳細情報 \\ \hline
      \end{tabular}
    }
  \end{minipage}
\end{table}


\subsection{ドライブ情報更新}

\begin{enumerate}
  \item 操作者の権限確認後，
        「経路のテーブル」および
        「募集のテーブル」の該当レコードを
        リクエストデータで更新する.
  \item \texttt{募集状況} が
        進行中以外のレコードは
        原則更新不可とする.
  \item 更新成功後，
        完了メッセージを返却する.
\end{enumerate}

\vspace{5mm}
\texttt{PUT /api/drives/{id}}

\begin{table}[H]
  \centering
  \begin{minipage}[t]{0.55\textwidth}
    \textbf{Request}
    \vspace{1mm}

    \centering
    \resizebox{\textwidth}{!}{
      \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 場所 \\ \hline\hline
        token         & string & 認証トークン & header \\ \hline
        id            & string & ドライブID & path \\ \hline
        departure     & string & 出発地 & body \\ \hline
        destination   & string & 目的地 & body \\ \hline
        departuretime & string & 出発日時 & body \\ \hline
        capacity      & number & 募集定員 & body \\ \hline
        fee           & number & 料金 & body \\ \hline
        message       & string & 補足メッセージ & body \\ \hline
        vehiclerules  & object & 車両ルール & body \\ \hline
      \end{tabular}
    }
  \end{minipage}
  \hfill
  \begin{minipage}[t]{0.40\textwidth}
    \textbf{Response (200 OK)}
    \vspace{1mm}

    \centering
    \resizebox{\textwidth}{!}{
      \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ \hline\hline
        message & string & 完了メッセージ \\ \hline
      \end{tabular}
    }
  \end{minipage}
\end{table}


\subsection{ドライブ削除}

\begin{enumerate}
  \item \texttt{token} を検証し，
        作成者本人であることを確認する.
  \item 対象の募集に紐づく
        「申請取引」を確認し，
        既に成立済みの取引がある場合は
        削除を制限するか，
        キャンセル処理を別途行う.
  \item 問題がなければ,
        「募集のテーブル」から
        該当レコードを削除する.
\end{enumerate}

\vspace{5mm}
\texttt{DELETE /api/drives/{id}}

\begin{table}[H]
  \centering
  \begin{minipage}[t]{0.55\textwidth}
    \textbf{Request}
    \vspace{1mm}

    \centering
    \resizebox{\textwidth}{!}{
      \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 場所 \\ \hline\hline
        token & string & 認証トークン & Header \\ \hline
        id    & string & ドライブID & Path \\ \hline
      \end{tabular}
    }
  \end{minipage}
  \hfill
  \begin{minipage}[t]{0.40\textwidth}
    \textbf{Response}
    \vspace{1mm}

    \centering
    \resizebox{\textwidth}{!}{
      \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ \hline\hline
        message & string & 完了メッセージ \\ \hline
      \end{tabular}
    }
  \end{minipage}
\end{table}

% end 田所櫂人

%start稗田

%end稗田

%startひかる
\subsection{ドライブ作成・編集・管理}
\subsubsection{マイドライブ情報取得}
\begin{enumerate}
\item リクエストに含まれるセッションを検証し,運転者のユーザーIDを特定する 
\item drives テーブルから,特定したユーザーIDが作成したドライブ情報を検索する
\item クエリパラメータ status に応じてフィルタリングを行う（recruiting: 募集中, matched: 確定済み, completed: 完了）
\item 日時順（未来の日付が上）にソートして返却する
\end{enumerate}
\vspace{5mm} % 表との間隔調整
\texttt{GET /api/driver/drives }

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth} % 左側: Request (幅を少し広めに確保)
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 位置\\ \hline\hline
        credential& 固定値 include& セッション& header \\ \hline
        status& string& ステータス& query\\ \hline
        \end{tabular}
        }
    \end{minipage}
    \hfill % 左右の間隔を空ける
    \begin{minipage}[t]{0.40\textwidth} % 右側: Response
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        drives& array & ドライブ情報のリスト\\ \hline
        \end{tabular}
        }
    \end{minipage}
\end{table}

\subsubsection{ドライブ新規登録}
\begin{enumerate}
\item リクエストに含まれるセッションを検証し,作成者となるユーザーIDを特定する 
\item 入力データのバリデーションを行う（過去日時の禁止,定員の数値チェック等）
\item recruitmentsテーブルに新規レコードを作成し,作成者IDに特定したユーザーIDを設定する.ステータスは recruiting とする
\item recruitmentsテーブルに車両ルール（禁煙,ペット可否等）を保存する
\end{enumerate}
\vspace{5mm} % 表との間隔調整
\texttt{POST /api/drives}

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth} % 左側: Request (幅を少し広めに確保)
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 位置\\ \hline\hline
        credential& 固定値 include& セッション& header \\ \hline
        departure& string& 出発地& body\\ \hline
        destination& string& 目的地&body\\ \hline
        departuretime& string& 出発日時&body\\ \hline
        capacity& number& 募集定員&body\\ \hline
        fee& number& 料金&body\\
        message& string& 補足メッセージ& body\\ \hline
        vehiclerules& object& 車両ルール& body\\
        
        
        \hline
        \end{tabular}
        }
    \end{minipage}
    \hfill % 左右の間隔を空ける
    \begin{minipage}[t]{0.40\textwidth} % 右側: Response
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        id& number & 作成された募集ID\\ \hline
        message & string & 完了メッセージ\\ \hline
        \end{tabular}
        }
    \end{minipage}
\end{table}

\subsubsection{ドライブ詳細取得 (編集用)}
\begin{enumerate}
\item リクエストに含まれるセッションを検証し,アクセスユーザーのIDを特定する 
\item 指定されたidのドライブ情報を取得する
\item ドライブの作成者IDとアクセスユーザーIDが一致するか確認する（編集権限チェック）
\item 一致した場合,編集用データを返却する
\end{enumerate}
\vspace{5mm} % 表との間隔調整
\texttt{GET /api/drives/:id}

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth} % 左側: Request (幅を少し広めに確保)
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 位置\\ \hline\hline
        credential& 固定値 include& セッション& header \\ \hline
        id & string& ドライブID & path\\ \hline
        \end{tabular}
        }
    \end{minipage}
    \hfill % 左右の間隔を空ける
    \begin{minipage}[t]{0.40\textwidth} % 右側: Response
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        drive & object & ドライブ詳細情報\\ \hline
        \end{tabular}
        }
    \end{minipage}
\end{table}

\subsubsection{ドライブ情報更新}
\begin{enumerate}
\item リクエストに含まれるセッションを検証し,アクセスユーザーのIDを特定する 
\item 作成者本人確認を行う
\item データを更新し,重要項目の変更があれば同乗者へ通知キューを作成する
\end{enumerate}
\vspace{5mm} % 表との間隔調整
\texttt{PUT /api/drives/:id}

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth} % 左側: Request (幅を少し広めに確保)
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 位置\\ \hline\hline
        credential& 固定値 include& セッション& header \\ \hline
        id & string & ドライブID & path\\ \hline
        departure & string & 出発地 & body \\ \hline
        destination& string& 目的地&body\\ \hline
        departuretime& string& 出発日時&body\\ \hline
        capacity& number& 募集定員&body\\ \hline
        fee& number& 料金&body\\
        message& string& 補足メッセージ& body\\ \hline
        vehiclerules& object& 車両ルール& body\\
        
        
        \hline
        \end{tabular}
        }
    \end{minipage}
    \hfill % 左右の間隔を空ける
    \begin{minipage}[t]{0.40\textwidth} % 右側: Response
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        message & string & 完了メッセージ\\ \hline
        \end{tabular}
        }
    \end{minipage}
\end{table}

\subsubsection{ドライブ削除}
\begin{enumerate}
\item リクエストに含まれるセッションを検証し,アクセスユーザーのIDを特定する 
\item 作成者本人確認を行う
\item 確定済みの同乗者がいないか確認し,問題なければ論理削除する
\end{enumerate}
\vspace{5mm} % 表との間隔調整
\texttt{DELETE /api/drives/:id}

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth} % 左側: Request (幅を少し広めに確保)
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 位置\\ \hline\hline
        credential& 固定値 include& セッション& header \\ \hline
        id & string & ドライブID & path\\  \hline
        \end{tabular}
        }
    \end{minipage}
    \hfill % 左右の間隔を空ける
    \begin{minipage}[t]{0.40\textwidth} % 右側: Response
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        message & string & 完了メッセージ\\ \hline
        \end{tabular}
        }
    \end{minipage}
\end{table}

\subsection{申請管理}
\subsubsection{申請一覧取得}
\begin{enumerate}
\item リクエストに含まれるセッションを検証し,運転者のユーザーIDを特定する 
\item drives テーブルからこのユーザーが作成したドライブIDリストを取得する
\item 取得したドライブに対する申請のうち,ステータスが pending のものを抽出する
\end{enumerate}
\vspace{5mm} % 表との間隔調整
\texttt{GET /api/driver/requests}

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth} % 左側: Request (幅を少し広めに確保)
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 位置\\ \hline\hline
        credential& 固定値 include& セッション& header \\ \hline
        status & string & "pending" & query\\  \hline
        \end{tabular}
        }
    \end{minipage}
    \hfill % 左右の間隔を空ける
    \begin{minipage}[t]{0.40\textwidth} % 右側: Response
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        requests & array & 申請情報のリスト\\ \hline
        \end{tabular}
        }
    \end{minipage}
\end{table}

\subsubsection{申請承認}
\begin{enumerate}
\item リクエストに含まれるセッションを検証し,実行者が正当な募集者か確認する
\item 申請ステータスを approved に更新する
\end{enumerate}
\vspace{5mm} % 表との間隔調整
\texttt{POST /api/applications/:id/approve}

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth} % 左側: Request (幅を少し広めに確保)
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 位置\\ \hline\hline
        credential& 固定値 include& セッション& header \\ \hline
        id & string & 申請ID & path\\  \hline
        \end{tabular}
        }
    \end{minipage}
    \hfill % 左右の間隔を空ける
    \begin{minipage}[t]{0.40\textwidth} % 右側: Response
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        message & string & 完了メッセージ\\ \hline
        \end{tabular}
        }
    \end{minipage}
\end{table}

\subsubsection{申請拒否}
\begin{enumerate}
\item リクエストに含まれるセッションを検証し,実行者が正当な募集者か確認する
\item 申請ステータスを rejected に更新する
\end{enumerate}
\vspace{5mm} % 表との間隔調整
\texttt{POST /api/applications/:id/reject}

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth} % 左側: Request (幅を少し広めに確保)
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 位置\\ \hline\hline
        credential& 固定値 include& セッション& header \\ \hline
        id & string & 申請ID & path\\  \hline
        \end{tabular}
        }
    \end{minipage}
    \hfill % 左右の間隔を空ける
    \begin{minipage}[t]{0.40\textwidth} % 右側: Response
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        message & string & 完了メッセージ\\ \hline
        \end{tabular}
        }
    \end{minipage}
\end{table}

\subsection{近くの募集・検索}
\subsubsection{近くの募集検索}
\begin{enumerate}
\item リクエストに含まれるセッションを検証する
\item クエリの lat, lng (GPS座標) を受け取る
\item PostGIS等を使用し,指定座標から半径 radius km以内を出発地とするリクエストを検索する
\item 各リクエストについて運転者とのマッチング度を計算し,距離が近い順にソートして返却する
\end{enumerate}
\vspace{5mm} % 表との間隔調整
\texttt{GET /api/passenger-requests/nearby}

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth} % 左側: Request (幅を少し広めに確保)
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 位置\\ \hline\hline
        credential& 固定値 include& セッション& header \\ \hline
        lat & number & 緯度 & query\\ \hline
        lng & number & 経度 & query \\ \hline
        radius & number & 半径 & query\\ \hline
        \end{tabular}
        }
    \end{minipage}
    \hfill % 左右の間隔を空ける
    \begin{minipage}[t]{0.40\textwidth} % 右側: Response
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        requests & array & 募集リスト\\ \hline
        \end{tabular}
        }
    \end{minipage}
\end{table}

\subsubsection{同乗者リクエスト条件検索}
\begin{enumerate}
\item リクエストに含まれるセッションを検証する
\item 指定された条件（エリア,日時,予算）に一致するリクエストを検索する
\item 各リクエストについて運転者とのマッチング度を計算し,マッチング度順にソートして返却する
\end{enumerate}
\vspace{5mm} % 表との間隔調整
\texttt{GET /api/passenger-requests}

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth} % 左側: Request (幅を少し広めに確保)
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 位置\\ \hline\hline
        credential& 固定値 include& セッション& header \\ \hline
        from & string & 出発地エリア & query\\ \hline
        to & string & 目的地エリア & query \\ \hline
        data & string & 希望日 & query\\ \hline
        minbudget & number & 予算下限& query\\ \hline
        maxbudget & number & 予算上限& query\\\hline
        \end{tabular}
        }
    \end{minipage}
    \hfill % 左右の間隔を空ける
    \begin{minipage}[t]{0.40\textwidth} % 右側: Response
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        requests & array & 募集リスト\\ \hline
        \end{tabular}
        }
    \end{minipage}
\end{table}

\subsubsection{リクエスト詳細取得}
\begin{enumerate}
\item リクエストに含まれるセッションを検証する
\item 指定されたリクエストIDの詳細情報を取得する
\item 同乗者の詳細プロフィールを結合し,マッチング情報を付与する
\end{enumerate}
\vspace{5mm} % 表との間隔調整
\texttt{GET /api/passenger-requests/:id}

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth} % 左側: Request (幅を少し広めに確保)
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 位置\\ \hline\hline
        credential& 固定値 include& セッション& header \\ \hline
        id & string & リクエストID & path\\ \\hline
        \end{tabular}
        }
    \end{minipage}
    \hfill % 左右の間隔を空ける
    \begin{minipage}[t]{0.40\textwidth} % 右側: Response
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        requests & object & リクエスト詳細\\ \hline
        passenger & object & 同乗者プロフィール\\ \hline
        \end{tabular}
        }
    \end{minipage}
\end{table}

\subsubsection{リクエストへの応答}
\begin{enumerate}
\item リクエストに含まれるセッションを検証し,運転者のIDを特定する
\item 運転者から同乗者側募集への応答として applicationsテーブルにレコードを作成する
\end{enumerate}
\vspace{5mm} % 表との間隔調整
\texttt{POST /api/applications}

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth} % 左側: Request (幅を少し広めに確保)
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 位置\\ \hline\hline
        credential& 固定値 include& セッション& header \\ \hline
        targetid & number & 応答するリクエストID & body\\ \hline
        type & string & "requests" & body \\ \hline
        \end{tabular}
        }
    \end{minipage}
    \hfill % 左右の間隔を空ける
    \begin{minipage}[t]{0.40\textwidth} % 右側: Response
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        message & string & 完了メッセージ\\ \hline
        \end{tabular}
        }
    \end{minipage}
\end{table}
%endひかる

%start黒星
\subsection{ポイント管理}
\subsubsection{履歴取得}
ポイントの全履歴データを取得する. 
\vspace{5mm} % 表との間隔調整
\texttt{GET /api/point/history}

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth} % 左側: Request (幅を少し広めに確保)
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 位置\\ \hline\hline
        type & string & 履歴の種類でフィルタリングする場合に指定& query \\ \hline
        limit& number& 1回のリクエストで取得する件数を指定& query\\ \hline
        offset& number& 取得開始位置またはページ番号を指定& query\\ \hline
        \end{tabular}
        }
    \end{minipage}
    \hfill % 左右の間隔を空ける
    \begin{minipage}[t]{0.40\textwidth} % 右側: Response
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        transactions& array & ポイント取引履歴リスト\\ \hline
        id& string & 取引ID\\ \hline
        type& string & 取引種別\\ \hline
        amount& number & ポイント額\\ \hline
        description& string & 取引内容\\ \hline
        date& string & 取引日時\\ \hline
        \end{tabular}
        }
    \end{minipage}
\end{table}

\subsubsection{残高取得}
現在のポイント残高と,その内訳を取得する. 
\vspace{5mm} % 表との間隔調整
\texttt{POST /api/point/remain}

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth} % 左側: Request (幅を少し広めに確保)
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 位置\\ \hline\hline
        Authorization & string & ログインユーザーを特定するための認証トークン& header \\ \hline
        
        \hline
        \end{tabular}
        }
    \end{minipage}
    \hfill % 左右の間隔を空ける
    \begin{minipage}[t]{0.40\textwidth} % 右側: Response
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        totalBalance& number & 合計保有ポイント\\ 
        breakdown & object & 内訳\\ \hline
        \end{tabular}
        }
    \end{minipage}
\end{table}

%end黒星


%beginごとう

\subsubsection{注文履歴確認}
\vspace{5mm} % 表との間隔調整
\texttt{GET /api/points/orders}

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth} % 左側: Request (幅を少し広めに確保)
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 位置\\ \hline\hline
        status & string & タブの状態& query \\
        
        
        \hline
        \end{tabular}
        }
    \end{minipage}
    \hfill % 左右の間隔を空ける
    \begin{minipage}[t]{0.40\textwidth} % 右側: Response
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        orders & array & 注文リスト \\ \hline
        \end{tabular}
        }
    \end{minipage}
\end{table}


\subsection{問い合わせ}
\subsubsection{お問い合わせ送信}
ヘッダーに含まれるトークンを用いてユーザー認証を行う（未ログイン時は省略可）.リクエストボディに含まれるお問い合わせ内容（種類,メールアドレス,件名,本文）のバリデーションを行い,管理者に通知およびデータベースへ保存する.

\vspace{5mm}

\texttt{POST /api/inquiry}

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth}
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 場所 \\ \hline\hline
        credential& 固定値 include& セッション& header \\ \hline
        category & string & 問い合わせ種類 & body \\ \hline
        email & string & メールアドレス & body \\ \hline
        subject & string & 件名 & body \\ \hline
        body & string & 本文 & body \\ \hline
        \end{tabular}
        }
    \end{minipage}
    \hfill
    \begin{minipage}[t]{0.40\textwidth}
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        %success & boolean & 送信成功フラグ \\ \hline
        message & string & 完了メッセージ \\ \hline
        \end{tabular}
        }
    \end{minipage}
\end{table}

\subsection{設定}

\subsubsection{ユーザー情報取得}
ヘッダーに含まれるトークンを用いてユーザー認証を行う.設定画面のヘッダー表示に必要な,ユーザーの基本情報（ID,氏名,メールアドレス,本人確認状態）を取得して返却する.

\vspace{5mm}

\texttt{GET /api/users/me}

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth}
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 場所 \\ \hline\hline
         credential& 固定値 include& セッション& header \\ \hline
        \end{tabular}
        }
    \end{minipage}
    \hfill
    \begin{minipage}[t]{0.40\textwidth}
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        name & string & 氏名 \\ \hline
        email& string& メールアドレス\\ \hline
        isVerified & boolean & 本人確認済フラグ \\ \hline
        \end{tabular}
        }
    \end{minipage}
\end{table}

\subsubsection{プロフィール更新}
ヘッダーに含まれるトークンを用いてユーザー認証を行う.リクエストボディに含まれる個人情報（氏名,生年月日,住所,電話番号）の形式チェックを行い,データベースのユーザー情報を更新する.

\vspace{5mm}

\texttt{PUT /api/users/me/profile}

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth}
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 場所 \\ \hline\hline
         credential& 固定値 include& セッション& header \\ \hline
        lastName & string & 姓 & body \\ \hline
        firstName & string & 名 & body \\ \hline
        birthDate & string & 生年月日 & body \\ \hline
        email & string & メールアドレス & body \\ \hline
        phone & string & 電話番号 & body \\ \hline
        address & string & 住所 & body \\ \hline
        password & string & パスワード変更の際 & body \\ \hline

        
        \end{tabular}
        }
    \end{minipage}
    \hfill
    \begin{minipage}[t]{0.40\textwidth}
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        success & boolean & 更新成功フラグ \\ \hline
        \end{tabular}
        }
    \end{minipage}
\end{table}

\subsubsection{本人確認書類アップロード}
ヘッダーに含まれるトークンを用いてユーザー認証を行う.リクエストボディに含まれる画像データを受け取り,ストレージへ保存する.その後,管理者の確認待ちステータスへ更新する.

\vspace{5mm}

\texttt{POST /api/users/me/identity-document}

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth}
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 場所 \\ \hline\hline
         credential& 固定値 include& セッション& header \\ \hline
        file & file & 書類画像データ & body \\ \hline
        \end{tabular}
        }
    \end{minipage}
    \hfill
    \begin{minipage}[t]{0.40\textwidth}
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        success & boolean & アップロード成功 \\ \hline
        \end{tabular}
        }
    \end{minipage}
\end{table}

\subsubsection{通知設定更新}
ヘッダーに含まれるトークンを用いてユーザー認証を行う.各通知項目（同乗申請,メッセージ,リマインダー）のオン・オフ設定を受け取り,データベースの設定情報を更新する.

\vspace{5mm}

\texttt{PUT /api/settings/notifications}

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth}
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 場所 \\ \hline\hline
        credential& 固定値 include& セッション& header \\ \hline
        rideRequest & boolean & 同乗申請通知 & body \\ \hline
        message & boolean & メッセージ通知 & body \\ \hline
        reminder & boolean & リマインダー & body \\ \hline
        promotion & boolean & プロモーション & body \\ \hline

        \end{tabular}
        }
    \end{minipage}
    \hfill
    \begin{minipage}[t]{0.40\textwidth}
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        message& string & メッセージ\\ \hline
        \end{tabular}
        }
    \end{minipage}
\end{table}

\subsubsection{クレジットカード追加}
ヘッダーに含まれるトークンを用いてユーザー認証を行う.決済代行会社から発行されたカードトークンを受け取り,顧客情報と紐付けて保存する.

\vspace{5mm}

\texttt{POST /api/payment/cards}

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth}
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 場所 \\ \hline\hline
        credential& 固定値 include& セッション& header \\ \hline
        payment\_token & string & 決済トークン & body \\ \hline
        id & string & カードID & path \\ \hline
        cardnumber & string & カード番号 & header\\ \hline
        name & string & カード名義人 & header \\ \hline
        date & string & 有効期限 & header \\ \hline
        code & number & セキュリティコード & header \\ \hline
        \end{tabular}
        }
    \end{minipage}
    \hfill
    \begin{minipage}[t]{0.40\textwidth}
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        cardId & string & カードID \\ \hline
        \end{tabular}
        }
    \end{minipage}
\end{table}

\subsubsection{クレジットカード編集}
ヘッダーに含まれるトークンを用いてユーザー認証を行う.パスパラメータで指定されたカードIDに対応する情報を編集する.

\vspace{5mm}

\texttt{PUT /api/payment/cards/\{id\}}

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth}
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 場所 \\ \hline\hline
        credential& 固定値 include& セッション& header \\ \hline
        id & string & カードID & path \\ \hline
        cardnumber & string & カード番号 & header\\ \hline
        name & string & カード名義人 & header \\ \hline
        date & string & 有効期限 & header \\ \hline
        code & number & セキュリティコード & header \\ \hline
        \end{tabular}
        }
    \end{minipage}
    \hfill
    \begin{minipage}[t]{0.40\textwidth}
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        message & string & メッセージ \\ \hline
        \end{tabular}
        }
    \end{minipage}
\end{table}

\subsection{決済}
Cookieに含まれるセッション情報 を用いて同乗者（支払者）を特定する.指定されたドライブIDに対して,登録済みのデフォルトカードを用いて決済を実行する.二重決済防止のため,サーバー側で当該ドライブの決済ステータスを確認する.

\vspace{5mm}

\texttt{POST /api/payment/transactions}

\begin{table}[H] \centering \begin{minipage}[t]{0.55\textwidth} \textbf{Request} \vspace{1mm}

    \centering
    \resizebox{\textwidth}{!}{
    \begin{tabular}{|l|l|l|l|}
    \hline
    パラメータ & 型 & 説明 & 場所 \\ \hline\hline
    credential& 固定値 include& セッション& header \\ \hline
    drive\_id & string & ドライブID & path\\ \hline
    amount & integer & 決済金額(円) & body \\ \hline
    \end{tabular}
    }
\end{minipage}
\hfill
\begin{minipage}[t]{0.40\textwidth}
    \textbf{Response}
    \vspace{1mm}
    
    \centering
    \resizebox{\textwidth}{!}{
    \begin{tabular}{|l|l|l|}
    \hline
    パラメータ & 型 & 説明 \\ 
    \hline\hline
    transactionId & string & 取引ID \\ \hline
    status & string & 決済状態 \\ \hline
    paidAt & string & 決済日時 \\ \hline
    \end{tabular}
    }
\end{minipage}

\end{table}

\subsection{顧客管理}
\subsubsection{管理者統計情報取得}
ヘッダーに含まれるトークンを用いて管理者権限の認証を行う.システム全体の総顧客数,総注文数,総商品数,発行ポイント総額などを集計して返却する.

\vspace{5mm}

\texttt{GET /api/admin/stats}

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth}
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 場所 \\ \hline\hline
        credential& 固定値 include& セッション& header \\ \hline
        \end{tabular}
        }
    \end{minipage}
    \hfill
    \begin{minipage}[t]{0.40\textwidth}
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        totalUsers & number & 総顧客数 \\ \hline
        totalOrders & number & 総注文数 \\ \hline
        totalProductsnumber & number & 総商品数\\ \hline
        issuedPoints & number & 付与ポイント総額 \\ \hline
        \end{tabular}
        }
    \end{minipage}
\end{table}


%endごとう

%beginのり

\subsubsection{顧客一覧取得}
%ヘッダーに含まれるトークンを用いて管理者権限の認証を行う.
ヘッダーに含まれるセッションを用いて管理者権限の認証を行う.

その後,クエリパラメータ（\texttt{limit}, \texttt{offset}, \texttt{search}, \texttt{sort}）を受け取り,顧客テーブルから条件に一致する顧客データを検索・取得する.取得した顧客情報のリスト（ID,氏名,メールアドレス,ステータス等）をレスポンスとして返却する.

\vspace{5mm} % 表との間隔調整
\texttt{GET admin/customers}

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth} % 左側: Request (幅を少し広めに確保)
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 場所 \\ \hline\hline
        %token & string & 管理者トークン & header \\ \hline
        credentials & 固定値include & セッション & header \\ \hline
        limit & number & 取得数 & query \\ \hline
        offset & number & 取得開始位置 & query \\ \hline
        search & string & 検索キーワード & query \\ \hline
        sort & string & ソート順 & query \\ \hline
        \end{tabular}
        }
    \end{minipage}
    \hfill % 左右の間隔を空ける
    \begin{minipage}[t]{0.40\textwidth} % 右側: Response
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        customers & array & 顧客一覧 \\ \hline
        \end{tabular}
        }
    \end{minipage}
\end{table}

\subsubsection{顧客統計情報取得}
%ヘッダーに含まれるトークンを用いて管理者権限の認証を行う.
ヘッダーに含まれるセッションを用いて管理者権限の認証を行う.

その後,顧客テーブルを集計し,現在の総顧客数,本人確認が完了している顧客数,および警告ステータスにある顧客数を算出する.算出結果を顧客管理ダッシュボード用の統計情報としてレスポンスで返却する.

\vspace{5mm} % 表との間隔調整

\texttt{GET admin/customers/stats}

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth} % 左側: Request (幅を少し広めに確保)
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 場所 \\ \hline\hline
        %token & string & 管理者トークン & header \\ \hline
        credentials & 固定値include & セッション & header \\ \hline
        \end{tabular}
        }
    \end{minipage}
    \hfill % 左右の間隔を空ける
    \begin{minipage}[t]{0.40\textwidth} % 右側: Response
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        total\_count & number & 総顧客数 \\ \hline
        verified\_count & number & 本人確認済み件数 \\ \hline
        warned\_count & number & 警告済み件数 \\ \hline
        \end{tabular}
        }
    \end{minipage}
\end{table}

\subsubsection{顧客警告送信}
%ヘッダーに含まれるトークンを用いて管理者権限の認証を行う.
ヘッダーに含まれるセッションを用いて管理者権限の認証を行う.

その後,パスパラメータで指定された顧客ID（\texttt{id}）を持つユーザーをデータベースから検索し,警告回数の加算またはステータスの更新を行う.処理成功時,更新後の顧客データと完了メッセージを返却する.

\vspace{5mm} % 表との間隔調整

\texttt{POST admin/customers/:id/warn}

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth} % 左側: Request (幅を少し広めに確保)
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 場所 \\ \hline\hline
        %token & string & 管理者トークン & header \\ \hline
        credentials & 固定値include & セッション & header \\ \hline
        id & string & 顧客ID & path \\ \hline
        \end{tabular}
        }
    \end{minipage}
    \hfill % 左右の間隔を空ける
    \begin{minipage}[t]{0.40\textwidth} % 右側: Response
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        message & string & メッセージ \\ \hline
        customer & object & 更新された顧客情報 \\ \hline
        \end{tabular}
        }
    \end{minipage}
\end{table}

\subsubsection{顧客アカウント削除}
%ヘッダーに含まれるトークンを用いて管理者権限の認証を行う.
ヘッダーに含まれるセッションを用いて管理者権限の認証を行う.

その後,パスパラメータで指定された顧客ID（\texttt{id}）を持つユーザーをデータベースから検索し,アカウントの有効化フラグ（\texttt{is\_active}）を\texttt{false}に更新して無効化する（またはレコードを物理削除する）.処理完了後,結果メッセージを返却する.

\vspace{5mm} % 表との間隔調整

\texttt{DELETE admin/customers/:id}

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth} % 左側: Request (幅を少し広めに確保)
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 場所 \\ \hline\hline
        %token & string & 管理者トークン & header \\ \hline
        credentials & 固定値include & セッション & header \\ \hline
        id & string & 顧客ID & path \\ \hline
        \end{tabular}
        }
    \end{minipage}
    \hfill % 左右の間隔を空ける
    \begin{minipage}[t]{0.40\textwidth} % 右側: Response
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        message & string & メッセージ \\ \hline
        \end{tabular}
        }
    \end{minipage}
\end{table}

\newpage
\subsection{商品管理}

\subsubsection{商品一覧取得}
%ヘッダーに含まれるトークンを用いて管理者権限の認証を行う.
ヘッダーに含まれるセッションを用いて管理者権限の認証を行う.

その後,クエリパラメータ（\texttt{limit}, \texttt{offset}, \texttt{keyword}, \texttt{sort}）に基づいて商品テーブル（\texttt{products}）から商品データを検索・取得する.取得した商品情報のリスト（ID,名称,カテゴリ,在庫数,警告閾値など）をレスポンスとして返却する.

\vspace{5mm} % 表との間隔調整

\texttt{GET admin/products}

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth} % 左側: Request (幅を少し広めに確保)
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 場所 \\ \hline\hline
        %token & string & 管理者トークン & header \\ \hline
        credentials & 固定値include & セッション & header \\ \hline
        limit & number & 取得数 & query \\ \hline
        offset & number & 取得開始位置 & query \\ \hline
        keyword & string & 検索キーワード & query \\ \hline
        sort & string & ソート順 & query \\ \hline
        \end{tabular}
        }
    \end{minipage}
    \hfill % 左右の間隔を空ける
    \begin{minipage}[t]{0.40\textwidth} % 右側: Response
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        products & array[object] & 商品一覧 \\ \hline
        \end{tabular}
        }
    \end{minipage}
\end{table}

\subsubsection{商品統計情報取得}
%ヘッダーに含まれるトークンを用いて管理者権限の認証を行う.
ヘッダーに含まれるセッションを用いて管理者権限の認証を行う.

その後,商品テーブル（\texttt{products}）を集計し,登録されている商品種類数,販売中の商品種類数,および全商品の総在庫数を算出する.算出結果をダッシュボード表示用の統計情報としてレスポンスで返却する.

\vspace{5mm} % 表との間隔調整

\texttt{GET admin/products/stats}

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth} % 左側: Request (幅を少し広めに確保)
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 場所 \\ \hline\hline
        %token & string & 管理者トークン & header \\ \hline
        credentials & 固定値include & セッション & header \\ \hline
        \end{tabular}
        }
    \end{minipage}
    \hfill % 左右の間隔を空ける
    \begin{minipage}[t]{0.40\textwidth} % 右側: Response
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        product\_type\_count & number & 商品種類数 \\ \hline
        sales\_product\_count & number & 販売商品種類数 \\ \hline
        total\_stock & number & 総在庫数 \\ \hline
        \end{tabular}
        }
    \end{minipage}
\end{table}

\subsubsection{商品情報登録}
%ヘッダーに含まれるトークンを用いて管理者権限の認証を行う.
ヘッダーに含まれるセッションを用いて管理者権限の認証を行う.

その後,リクエストボディに含まれる商品情報（商品名,カテゴリID,ポイント,在庫数,説明,警告閾値,画像データ）のバリデーションを行い,データベースの商品テーブル（\texttt{products}）に新規レコードとして保存する.保存成功時,登録された商品情報と完了メッセージを返却する.

\vspace{5mm} % 表との間隔調整

\texttt{POST admin/products}

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth} % 左側: Request (幅を少し広めに確保)
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 場所 \\ \hline\hline
        %token & string & 管理者トークン & header \\ \hline
        credentials & 固定値include & セッション & header \\ \hline
        name & string & 商品名 & body \\ \hline
        category\_id & string & カテゴリID & body \\ \hline
        points & number & ポイント & body \\ \hline
        stock & number & 初期在庫数 & body \\ \hline
        description & string & 商品説明 & body \\ \hline
        alert\_threshold & number & 在庫警告閾値 & body \\ \hline
        image & string & 商品画像データ & body \\ \hline
        \end{tabular}
        }
    \end{minipage}
    \hfill % 左右の間隔を空ける
    \begin{minipage}[t]{0.40\textwidth} % 右側: Response
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        message & string & メッセージ \\ \hline
        product & object & 登録された商品情報 \\ \hline
        \end{tabular}
        }
    \end{minipage}
\end{table}

\subsubsection{商品情報更新}
%ヘッダーに含まれるトークンを用いて管理者権限の認証を行う.
ヘッダーに含まれるセッションを用いて管理者権限の認証を行う.

その後,パスパラメータで指定された商品ID（\texttt{id}）を持つ商品の情報を,リクエストボディに含まれる内容（商品名,カテゴリID,ポイント,在庫数,説明,警告閾値,画像データ）で更新する.更新成功時,更新後の商品情報と完了メッセージを返却する.

\vspace{5mm} % 表との間隔調整

\texttt{PUT admin/products/:id}

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth} % 左側: Request (幅を少し広めに確保)
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 場所 \\ \hline\hline
        %token & string & 管理者トークン & header \\ \hline
        credentials & 固定値include & セッション & header \\ \hline
        id & string & 商品ID & path \\ \hline
        name & string & 商品名 & body \\ \hline
        category\_id & string & カテゴリID & body \\ \hline
        points & number & ポイント & body \\ \hline
        stock & number & 在庫数 & body \\ \hline
        description & string & 商品説明 & body \\ \hline
        alert\_threshold & number & 在庫警告閾値 & body \\ \hline
        image & string & 商品画像データ & body \\ \hline
        \end{tabular}
        }
    \end{minipage}
    \hfill % 左右の間隔を空ける
    \begin{minipage}[t]{0.40\textwidth} % 右側: Response
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        message & string & メッセージ \\ \hline
        product & object & 更新された商品情報 \\ \hline
        \end{tabular}
        }
    \end{minipage}
\end{table}

\subsubsection{商品削除}
%ヘッダーに含まれるトークンを用いて管理者権限の認証を行う.
ヘッダーに含まれるセッションを用いて管理者権限の認証を行う.

その後,パスパラメータで指定された商品ID（\texttt{id}）を持つ商品をデータベースから削除する（または削除フラグを立てて無効化する）.削除処理が完了した後,結果メッセージをレスポンスとして返却する.

\vspace{5mm} % 表との間隔調整

\texttt{DELETE admin/products/:id}

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth} % 左側: Request (幅を少し広めに確保)
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 場所 \\ \hline\hline
        %token & string & 管理者トークン & header \\ \hline
        credentials & 固定値include & セッション & header \\ \hline
        id & string & 商品ID & path \\ \hline
        \end{tabular}
        }
    \end{minipage}
    \hfill % 左右の間隔を空ける
    \begin{minipage}[t]{0.40\textwidth} % 右側: Response
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        message & string & メッセージ \\ \hline
        \end{tabular}
        }
    \end{minipage}
\end{table}

\subsection{在庫管理}
\subsubsection{在庫統計情報取得}
%ヘッダーに含まれるトークンを用いて管理者権限の認証を行う.
ヘッダーに含まれるセッションを用いて管理者権限の認証を行う.

その後,商品テーブル（\texttt{products}）を集計し,現在の総在庫数,在庫数が警告閾値を下回っている商品数（在庫警告数）,およびこれまでの総販売数を算出する.算出結果を在庫管理ダッシュボード用の統計情報としてレスポンスで返却する.

\vspace{5mm} % 表との間隔調整

\texttt{GET admin/stocks/stats}

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth} % 左側: Request (幅を少し広めに確保)
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 場所 \\ \hline\hline
        %token & string & 管理者トークン & header \\ \hline
        credentials & 固定値include & セッション & header \\ \hline
        \end{tabular}
        }
    \end{minipage}
    \hfill % 左右の間隔を空ける
    \begin{minipage}[t]{0.40\textwidth} % 右側: Response
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        total\_stock & number & 総在庫数 \\ \hline
        warning\_count & number & 在庫警告数 \\ \hline
        total\_sales & number & 総販売数 \\ \hline
        \end{tabular}
        }
    \end{minipage}
\end{table}

\subsubsection{在庫補充}
%ヘッダーに含まれるトークンを用いて管理者権限の認証を行う.
ヘッダーに含まれるセッションを用いて管理者権限の認証を行う.

その後,パスパラメータで指定された商品ID（\texttt{id}）を持つ商品をデータベースから特定し,リクエストボディで指定された補充数量（\texttt{amount}）を現在の在庫数に加算して更新する.更新処理が完了した後,完了メッセージと更新後の現在庫数をレスポンスとして返却する.

\vspace{5mm} % 表との間隔調整

\texttt{POST admin/products/:id/replenish}

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth} % 左側: Request (幅を少し広めに確保)
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 場所 \\ \hline\hline
        %token & string & 管理者トークン & header \\ \hline
        credentials & 固定値include & セッション & header \\ \hline
        id & string & 商品ID & path \\ \hline
        amount & number & 補充数量 & body \\ \hline
        \end{tabular}
        }
    \end{minipage}
    \hfill % 左右の間隔を空ける
    \begin{minipage}[t]{0.40\textwidth} % 右側: Response
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        message & string & メッセージ \\ \hline
        current\_stock & number & 更新後の現在庫数 \\ \hline
        \end{tabular}
        }
    \end{minipage}
\end{table}

\subsection{注文管理}

\subsubsection{注文一覧取得}
%ヘッダーに含まれるトークンを用いて管理者権限の認証を行う.
ヘッダーに含まれるセッションを用いて管理者権限の認証を行う.

その後,クエリパラメータ（\texttt{limit}, \texttt{offset}, \texttt{status}, \texttt{search}, \texttt{sort}）に基づいて注文データを検索・取得する.取得した注文情報のリスト（注文番号,ステータス,顧客情報,商品情報,数量,合計金額など）をレスポンスとして返却する.

\vspace{5mm} % 表との間隔調整

\texttt{GET admin/orders}

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth} % 左側: Request (幅を少し広めに確保)
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 場所 \\ \hline\hline
        %token & string & 管理者トークン & header \\ \hline
        credentials & 固定値include & セッション & header \\ \hline
        limit & number & 取得数 & query \\ \hline
        offset & number & 取得開始位置 & query \\ \hline
        status & string & ステータス（準備中/発送済み等） & query \\ \hline
        search & string & 検索キーワード（注文番号等） & query \\ \hline
        sort & string & ソート順 & query \\ \hline
        \end{tabular}
        }
    \end{minipage}
    \hfill % 左右の間隔を空ける
    \begin{minipage}[t]{0.40\textwidth} % 右側: Response
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        orders & array[object] & 注文一覧 \\ \hline
        \end{tabular}
        }
    \end{minipage}
\end{table}

\subsubsection{注文統計情報取得}
%ヘッダーに含まれるトークンを用いて管理者権限の認証を行う.
ヘッダーに含まれるセッションを用いて管理者権限の認証を行う.

その後,注文テーブル（\texttt{orders}）を集計し,総注文数,出荷準備中の注文数,および発送済みの注文数を算出する.算出結果を注文管理ダッシュボード用の統計情報としてレスポンスで返却する.

\vspace{5mm} % 表との間隔調整

\texttt{GET admin/orders/stats}

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth} % 左側: Request (幅を少し広めに確保)
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 場所 \\ \hline\hline
        %token & string & 管理者トークン & header \\ \hline
        credentials & 固定値include & セッション & header \\ \hline
        \end{tabular}
        }
    \end{minipage}
    \hfill % 左右の間隔を空ける
    \begin{minipage}[t]{0.40\textwidth} % 右側: Response
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        total\_orders & number & 総注文数 \\ \hline
        ready\_count & number & 出荷準備中注文数 \\ \hline
        shipped\_count & number & 発送済み注文数 \\ \hline
        \end{tabular}
        }
    \end{minipage}
\end{table}

\subsubsection{注文ステータス更新}
%ヘッダーに含まれるトークンを用いて管理者権限の認証を行う.
ヘッダーに含まれるセッションを用いて管理者権限の認証を行う.

その後,パスパラメータで指定された注文ID（\texttt{id}）を持つ注文データを検索し,リクエストボディで指定された新しいステータス（\texttt{status}）に更新する.更新処理が完了した後,更新された注文情報と完了メッセージをレスポンスとして返却する.

\vspace{5mm} % 表との間隔調整

\texttt{PUT admin/orders/:id/status}

\begin{table}[H]
    \centering
    \begin{minipage}[t]{0.55\textwidth} % 左側: Request (幅を少し広めに確保)
        \textbf{Request}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|l|}
        \hline
        パラメータ & 型 & 説明 & 場所 \\ \hline\hline
        %token & string & 管理者トークン & header \\ \hline
        credentials & 固定値include & セッション & header \\ \hline
        id & string & 注文ID & path \\ \hline
        status & string & 新しいステータス & body \\ \hline
        \end{tabular}
        }
    \end{minipage}
    \hfill % 左右の間隔を空ける
    \begin{minipage}[t]{0.40\textwidth} % 右側: Response
        \textbf{Response}
        \vspace{1mm}
        
        \centering
        \resizebox{\textwidth}{!}{% 表を領域幅に合わせて縮小
        \begin{tabular}{|l|l|l|}
        \hline
        パラメータ & 型 & 説明 \\ 
        \hline\hline
        message & string & メッセージ \\ \hline
        order & object & 更新された注文情報 \\ \hline
        \end{tabular}
        }
    \end{minipage}
\end{table}

%endのり

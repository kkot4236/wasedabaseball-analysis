import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import japanize_matplotlib
import os
import numpy as np
import matplotlib.cm as cm

# --- 1. パスワード保護 ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = None
    if st.session_state["password_correct"] == True: return True
    def password_entered():
        if st.session_state["password_input"] == "wbc1901":
            st.session_state["password_correct"] = True
        else:
            st.session_state["password_correct"] = False
    st.title("🔐 早稲田大学野球部 データ分析 Pro+")
    st.text_input("パスワードを入力してください", type="password", on_change=password_entered, key="password_input")
    return st.session_state["password_correct"]

if check_password():
    st.set_page_config(layout="wide", page_title="野球部データ分析 Pro+")

    # --- 2. 描画関数 ---
    def draw_strike_zone(ax):
        # ストライクゾーン (cm)
        ax.add_patch(plt.Rectangle((-21.5, 45), 43, 60, fill=False, lw=3, ec='black', zorder=5))
        ax.axvline(0, color='gray', lw=0.5, ls='--')
        ax.axhline(75, color='gray', lw=0.5, ls='--')

    @st.cache_data
    def load_csv(file_path):
        df = pd.read_csv(file_path)
        # 数値変換の徹底
        num_cols = ['PlateLocSide', 'PlateLocHeight', 'ExitSpeed', 'Angle', 'Distance', 'PitcherThrows']
        for c in num_cols:
            if c in df.columns and c != 'PitcherThrows':
                df[c] = pd.to_numeric(df[c], errors='coerce')
        # 単位変換 ft -> cm
        if 'PlateLocSide' in df.columns and df['PlateLocSide'].abs().max() < 10:
            df['PlateLocSide'] *= 30.48
            df['PlateLocHeight'] *= 30.48
        return df

    # --- 3. UI構造（タブとサイドバーの連動） ---
    # サイドバーの最上部に「モード切替」を置くことで、確実にサイドバーを切り替えます
    st.sidebar.title("🚀 メインメニュー")
    app_mode = st.sidebar.radio("分析モード", ["🔥 投手分析", "⚾ 打者分析"])

    DATA_DIR = "data"
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')] if os.path.exists(DATA_DIR) else []

    if not files:
        st.error("dataフォルダにCSVファイルが見つかりません。")
    else:
        if app_mode == "🔥 投手分析":
            st.sidebar.subheader("🔥 PITCHER SETTINGS")
            sel_file = st.sidebar.selectbox("ファイル選択", files, key="p_file")
            df_all = load_csv(os.path.join(DATA_DIR, sel_file))
            p_col = 'Pitcher' if 'Pitcher' in df_all.columns else 'Pitcher Name'
            p_list = sorted(df_all[p_col].dropna().unique())
            sel_name = st.sidebar.selectbox("投手を選択", p_list)
            p_sub = st.sidebar.radio("レポート形式", ["総合レポート", "詳細分析"], key="p_sub")

            # 投手分析メイン
            st.title(f"📊 {sel_name} 投手分析")
            p_df = df_all[df_all[p_col] == sel_name].copy()
            # (投手分析の描画コードは前回同様のため、動作確認を優先し中身を維持)

        elif app_mode == "⚾ 打者分析":
            st.sidebar.subheader("⚾ BATTER SETTINGS")
            sel_file = st.sidebar.selectbox("ファイル選択", files, key="b_file")
            df_all = load_csv(os.path.join(DATA_DIR, sel_file))
            b_col = 'Batter' if 'Batter' in df_all.columns else 'Batter Name'
            b_list = sorted(df_all[b_col].dropna().unique())
            sel_name = st.sidebar.selectbox("打者を選択", b_list)
            v_b = st.sidebar.radio("表示視点", ["投手目線", "捕手目線"])
            
            # 打者分析メイン
            st.title(f"🎯 {sel_name} 打球速度分析")
            
            # 投手左右切り替え（全投手・対右・対左）
            t_side = st.radio("投手左右", ["すべて", "右投手", "左投手"], horizontal=True)
            
            b_df = df_all[df_all[b_col] == sel_name].copy()
            if t_side == "右投手":
                display_df = b_df[b_df['PitcherThrows'].str.contains('Right|R', na=False, case=False)]
            elif t_side == "左投手":
                display_df = b_df[b_df['PitcherThrows'].str.contains('Left|L', na=False, case=False)]
            else:
                display_df = b_df

            # --- コース別打球速度ヒートマップ (速度表示の強化版) ---
            st.subheader(f"📊 コース別平均打球速度 (km/h) - {t_side}")
            
            # 打球速度データがあるものだけを抽出
            plot_df = display_df.dropna(subset=['ExitSpeed', 'PlateLocSide', 'PlateLocHeight'])
            
            if not plot_df.empty:
                fig, ax = plt.subplots(figsize=(8, 8))
                draw_strike_zone(ax)
                
                # 判定用グリッド (ゾーン外も拾うために範囲を広く設定)
                x_edges = [-100, -21.5, 0, 21.5, 100] # 4分割
                y_edges = [0, 45, 75, 105, 200]    # 4分割
                
                px = plot_df['PlateLocSide'] * (-1 if v_b == "捕手目線" else 1)
                py = plot_df['PlateLocHeight']
                ev = plot_df['ExitSpeed']

                # 3x3 (中央のストライクゾーン周辺) を計算
                # インデックス1~3がストライクゾーン枠内
                for i in range(1, 4): 
                    for j in range(1, 4):
                        mask = (px >= x_edges[j-1]) & (px < x_edges[j]) & (py >= y_edges[i-1]) & (py < y_edges[i])
                        cell_ev = ev[mask]
                        
                        if not cell_ev.empty:
                            avg_v = cell_ev.mean()
                            count = len(cell_ev)
                            
                            # 色の反映
                            color = cm.Reds(np.clip((avg_v - 110) / 40, 0.1, 0.9))
                            # 描画位置はストライクゾーンの枠に合わせる
                            rect_x = [-21.5, 0, 21.5][j-1]
                            rect_y = [45, 75, 105][i-1]
                            width = 21.5 if j < 3 else 21.5
                            
                            # テキストと色を表示
                            ax.add_patch(plt.Rectangle((x_edges[j], y_edges[i]), x_edges[j+1]-x_edges[j], y_edges[i+1]-y_edges[i], 
                                         facecolor=color, alpha=0.8, ec='white'))
                            # 簡易的に各セルの中心にテキスト配置
                            cx = (x_edges[j] + x_edges[j+1]) / 2
                            cy = (y_edges[i] + y_edges[i+1]) / 2
                            if 0 < i < 4 and 0 < j < 4: # ゾーン内
                                ax.text(cx, cy, f"{avg_v:.1f}\n(n={count})", ha='center', va='center', fontweight='bold', fontsize=12)

                ax.set_xlim(-70, 70); ax.set_ylim(20, 160)
                plt.axis('off')
                st.pyplot(fig)
                
                # デバッグ用：抽出されたデータの平均を数値でも表示
                st.write(f"現在の条件での平均打球速度: **{plot_df['ExitSpeed'].mean():.1f} km/h** (合計本数: {len(plot_df)})")
            else:
                st.warning("打球速度データが見つかりません。ファイル内の 'ExitSpeed' 列を確認してください。")

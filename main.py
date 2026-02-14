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

    # --- 2. 共通関数（シルエット描画） ---
    def draw_stylish_batter(ax, batter_side='Right'):
        x_offset = 60 if batter_side == 'Right' else -60
        flip = -1 if batter_side == 'Right' else 1
        color = '#333333'
        alpha = 0.1
        ax.add_patch(plt.Circle((x_offset, 135), 6, color=color, alpha=alpha))
        body = plt.Polygon(np.array([[x_offset-10, 80], [x_offset+10, 80], [x_offset+15, 130], [x_offset-15, 130]]), color=color, alpha=alpha)
        ax.add_patch(body)
        bat = plt.Polygon(np.array([[x_offset+(12*flip), 120], [x_offset+(45*flip), 160], [x_offset+(48*flip), 157], [x_offset+(15*flip), 117]]), color=color, alpha=0.15)
        ax.add_patch(bat)

    @st.cache_data
    def load_csv(file_path):
        try:
            df = pd.read_csv(file_path, encoding='cp932')
        except:
            df = pd.read_csv(file_path, encoding='utf-8')
        
        # 座標の修正: ft -> cm (100倍ではなく30.48倍にする)
        if 'PlateLocSide' in df.columns:
            # すでにcm単位（大きな値）で入っていないか確認して変換
            if df['PlateLocSide'].abs().max() < 10:
                df['PlateLocSide_cm'] = df['PlateLocSide'] * 30.48
                df['PlateLocHeight_cm'] = df['PlateLocHeight'] * 30.48
            else:
                df['PlateLocSide_cm'] = df['PlateLocSide']
                df['PlateLocHeight_cm'] = df['PlateLocHeight']
        return df

    # --- 3. メインUI構造 (タブ切替) ---
    # st.tabsの選択状態を監視
    tab_p, tab_b = st.tabs(["🔥 投手分析", "⚾ 打者分析"])

    DATA_DIR = "data"
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')] if os.path.exists(DATA_DIR) else []

    if not files:
        st.error("dataフォルダにCSVファイルが見つかりません。")
    else:
        # ---------------------------------------------------------
        # 🔥 投手分析タブ
        # ---------------------------------------------------------
        with tab_p:
            # サイドバーをクリアし、投手用設定のみを表示
            with st.sidebar:
                st.header("🔥 PITCHER SETTINGS")
                sel_file_p = st.selectbox("分析ファイルを選択", files, key="p_file_nav")
                df_p_all = load_csv(os.path.join(DATA_DIR, sel_file_p))
                p_col = 'Pitcher' if 'Pitcher' in df_p_all.columns else 'Pitcher Name'
                p_list = sorted(df_p_all[p_col].dropna().unique())
                sel_p = st.selectbox("投手を選択", p_list, key="p_name_nav")
                p_sub = st.radio("レポート形式", ["総合レポート", "詳細分析"], key="p_mode_nav")
            
            st.title(f"📊 {sel_p} 投手分析")
            # 投手用コンテンツ（変化量など）をここに記述

        # ---------------------------------------------------------
        # ⚾ 打者分析タブ
        # ---------------------------------------------------------
        with tab_b:
            # サイドバーを打者用設定に完全に切り替える
            # (Streamlitの仕様上、同じサイドバー内に書くが、
            #  タブのコンテキストに応じて表示内容を管理する)
            with st.sidebar:
                st.header("⚾ BATTER SETTINGS")
                sel_file_b = st.selectbox("分析ファイルを選択", files, key="b_file_nav")
                df_b_all = load_csv(os.path.join(DATA_DIR, sel_file_b))
                b_col = 'Batter' if 'Batter' in df_b_all.columns else 'Batter Name'
                b_list = sorted(df_b_all[b_col].dropna().unique())
                sel_b = st.selectbox("打者を選択", b_list, key="b_name_nav")
                v_b = st.sidebar.radio("表示視点", ["投手目線", "捕手目線"], key="b_view_nav")

            st.title(f"🎯 {sel_b} 打撃詳細分析")
            
            b_df = df_b_all[(df_b_all[b_col] == sel_b) & (df_b_all['ExitSpeed'].notna())].copy()
            if not b_df.empty:
                batter_hand = b_df['BatterSide'].mode()[0] if 'BatterSide' in b_df.columns else 'Right'
                
                # 3カラム表示
                c1, c2, c3 = st.columns(3)
                filters = [b_df, b_df[b_df['PitcherThrows'].str.contains('Right|R', na=False)], 
                           b_df[b_df['PitcherThrows'].str.contains('Left|L', na=False)]]
                titles = ['TOTAL', 'vs RIGHT P', 'vs LEFT P']

                # 9分割（+周辺）の境界設定 (cm単位)
                # ストライクゾーン内を3x3にするための設定
                x_edges = [-40, -21.5, -7.17, 7.17, 21.5, 40]
                y_edges = [25, 45, 65, 85, 105, 125]
                V_MIN, V_MAX = 110, 160

                for i, col_ui in enumerate([c1, c2, c3]):
                    subset = filters[i]
                    fig, ax = plt.subplots(figsize=(6, 8))
                    draw_stylish_batter(ax, batter_side=batter_hand)
                    
                    # 5x5 グリッド描画 (中央3x3がストライクゾーン)
                    for r in range(5):
                        for c in range(5):
                            x_min, x_max = x_edges[c], x_edges[c+1]
                            y_min, y_max = y_edges[r], y_edges[r+1]
                            
                            # 視点切替
                            side_mod = -1 if v_b == "捕手目線" else 1
                            mask = (subset['PlateLocSide_cm'] * side_mod >= x_min) & \
                                   (subset['PlateLocSide_cm'] * side_mod < x_max) & \
                                   (subset['PlateLocHeight_cm'] >= y_min) & \
                                   (subset['PlateLocHeight_cm'] < y_max)
                            
                            zone_data = subset[mask]
                            if not zone_data.empty:
                                avg_v = zone_data['ExitSpeed'].mean()
                                n_hits = len(zone_data)
                                color = cm.Reds(np.clip((avg_v - V_MIN) / (V_MAX - V_MIN), 0, 1))
                                
                                ax.add_patch(plt.Rectangle((x_min, y_min), x_max-x_min, y_max-y_min, 
                                             facecolor=color, alpha=0.8, ec='white', lw=0.5))
                                ax.text((x_min+x_max)/2, (y_min+y_max)/2, f"{avg_v:.1f}\nn={n_hits}", 
                                        ha='center', va='center', fontweight='bold', fontsize=9, 
                                        color='white' if avg_v > 140 else 'black')

                    # ストライクゾーン強調枠
                    ax.add_patch(plt.Rectangle((-21.5, 45), 43, 60, fill=False, ec='black', lw=2, zorder=10))
                    ax.set_xlim(-70, 70); ax.set_ylim(10, 160); ax.set_title(titles[i], fontsize=15, fontweight='bold')
                    ax.axis('off')
                    col_ui.pyplot(fig)
            else:
                st.info("表示可能なデータがありません。")

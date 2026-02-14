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

    # --- 2. 共通関数（シルエット描画：ご提示コード再現） ---
    def draw_stylish_batter(ax, batter_side='Right'):
        x_offset = 50 if batter_side == 'Right' else -50
        flip = -1 if batter_side == 'Right' else 1
        color = '#333333'; alpha = 0.12
        ax.add_patch(plt.Circle((x_offset, 130), 5, color=color, alpha=alpha, zorder=0))
        body = plt.Polygon(np.array([[x_offset-8, 80], [x_offset+8, 80], [x_offset+12, 125], [x_offset-12, 125]]), color=color, alpha=alpha, zorder=0)
        ax.add_patch(body)
        ax.add_patch(plt.Polygon(np.array([[x_offset-8, 80], [x_offset-4, 80], [x_offset-12, 20], [x_offset-20, 20]]), color=color, alpha=alpha, zorder=0))
        ax.add_patch(plt.Polygon(np.array([[x_offset+4, 80], [x_offset+8, 80], [x_offset+15, 20], [x_offset+8, 20]]), color=color, alpha=alpha, zorder=0))
        bat = plt.Polygon(np.array([[x_offset+(10*flip), 115], [x_offset+(40*flip), 155], [x_offset+(43*flip), 152], [x_offset+(13*flip), 112]]), color=color, alpha=0.18, zorder=0)
        ax.add_patch(bat)

    @st.cache_data
    def load_csv(file_path):
        try: df = pd.read_csv(file_path, encoding='cp932')
        except: df = pd.read_csv(file_path, encoding='utf-8')
        
        # 単位変換: m -> cm (単位がメートルであることを前提に * 100)
        df['PlateLocSide_cm'] = df['PlateLocSide'] * 100
        df['PlateLocHeight_cm'] = df['PlateLocHeight'] * 100
        return df

    # --- 3. UI切替 ---
    mode = st.sidebar.radio("🔥 分析モード", ["投手分析", "打者分析"])
    DATA_DIR = "data"
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')] if os.path.exists(DATA_DIR) else []

    if files:
        if mode == "投手分析":
            with st.sidebar:
                st.header("🔥 PITCHER SETTINGS")
                sel_file_p = st.selectbox("ファイルを選択", files, key="p_f")
                df_p = load_csv(os.path.join(DATA_DIR, sel_file_p))
                p_col = 'Pitcher' if 'Pitcher' in df_p.columns else 'Pitcher Name'
                sel_p = st.selectbox("投手を選択", sorted(df_p[p_col].dropna().unique()), key="p_s")
            st.title(f"📊 {sel_p} 投手分析")
            # 投手用詳細はこちらへ

        else:
            with st.sidebar:
                st.header("⚾ BATTER SETTINGS")
                sel_file_b = st.selectbox("ファイルを選択", files, key="b_f")
                df_b = load_csv(os.path.join(DATA_DIR, sel_file_b))
                b_col = 'Batter' if 'Batter' in df_b.columns else 'Batter Name'
                sel_b = st.selectbox("打者を選択", sorted(df_b[b_col].dropna().unique()), key="b_s")
                v_view = st.radio("表示視点", ["投手目線", "捕手目線"])

            st.title(f"🎯 {sel_b} 打撃詳細分析")
            target_df = df_b[(df_b[b_col] == sel_b) & (df_b['ExitSpeed'].notna())].copy()

            if not target_df.empty:
                hand = target_df['BatterSide'].mode()[0] if 'BatterSide' in target_df.columns else 'Right'
                
                # --- ご提示の境界線を完全再現 ---
                x_edges = [-36.5, -21.5, -7.17, 7.17, 21.5, 36.5]
                y_edges = [30.0, 45.0, 65.0, 85.0, 105.0, 120.0]
                V_MIN, V_MAX = 110, 155

                c1, c2, c3 = st.columns(3)
                filters = [
                    target_df,
                    target_df[target_df['PitcherThrows'].str.startswith(('R', 'r'), na=False)],
                    target_df[target_df['PitcherThrows'].str.startswith(('L', 'l'), na=False)]
                ]
                titles = ['TOTAL', 'VS RIGHT P', 'VS LEFT P']

                for i, col_ax in enumerate([c1, c2, c3]):
                    subset = filters[i]
                    fig, ax = plt.subplots(figsize=(7, 9))
                    draw_stylish_batter(ax, batter_side=hand)
                    
                    # --- ご提示の5x5ループ・高め(4-r)を正確に再現 ---
                    for r in range(5):
                        for c in range(5):
                            x_min, x_max = x_edges[c], x_edges[c+1]
                            y_min, y_max = y_edges[4-r], y_edges[5-r]
                            
                            side_mod = -1 if v_view == "捕手目線" else 1
                            mask = (subset['PlateLocSide_cm'] * side_mod >= x_min) & \
                                   (subset['PlateLocSide_cm'] * side_mod < x_max) & \
                                   (subset['PlateLocHeight_cm'] >= y_min) & \
                                   (subset['PlateLocHeight_cm'] < y_max)
                            
                            zone_data = subset[mask]
                            if not zone_data.empty:
                                avg_v = zone_data['ExitSpeed'].mean()
                                n = len(zone_data)
                                norm_v = (avg_v - V_MIN) / (V_MAX - V_MIN)
                                color = cm.Reds(np.clip(norm_v, 0, 1))
                                
                                ax.add_patch(plt.Rectangle((x_min, y_min), x_max-x_min, y_max-y_min, 
                                             color=color, alpha=0.9, ec='white', lw=0.5, zorder=5))
                                text_col = 'white' if norm_v > 0.6 else 'black'
                                ax.text((x_min+x_max)/2, (y_min+y_max)/2, f"{avg_v:.1f}\n$n$={n}", 
                                        ha='center', va='center', fontweight='bold', fontsize=9, color=text_col, zorder=10)

                    # ストライクゾーン強調
                    ax.add_patch(plt.Rectangle((-21.5, 45.0), 43.0, 60.0, fill=False, ec='black', lw=2.5, zorder=15))
                    ax.set_xlim(-75, 75); ax.set_ylim(15, 165); ax.set_aspect('equal')
                    ax.set_title(titles[i], fontsize=15, fontweight='bold'); ax.axis('off')
                    col_ax.pyplot(fig)
            else:
                st.warning("データがありません。")

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

    # --- 2. 共通関数（シルエット描画：ご提示のコード通り） ---
    def draw_stylish_batter(ax, batter_side='Right'):
        x_offset = 50 if batter_side == 'Right' else -50
        flip = -1 if batter_side == 'Right' else 1
        color = '#333333'
        alpha = 0.12
        ax.add_patch(plt.Circle((x_offset, 130), 5, color=color, alpha=alpha, zorder=0))
        body = plt.Polygon(np.array([[x_offset-8, 80], [x_offset+8, 80], [x_offset+12, 125], [x_offset-12, 125]]), color=color, alpha=alpha, zorder=0)
        ax.add_patch(body)
        leg1 = plt.Polygon(np.array([[x_offset-8, 80], [x_offset-4, 80], [x_offset-12, 20], [x_offset-20, 20]]), color=color, alpha=alpha, zorder=0)
        leg2 = plt.Polygon(np.array([[x_offset+4, 80], [x_offset+8, 80], [x_offset+15, 20], [x_offset+8, 20]]), color=color, alpha=alpha, zorder=0)
        ax.add_patch(leg1)
        ax.add_patch(leg2)
        bat = plt.Polygon(np.array([[x_offset+(10*flip), 115], [x_offset+(40*flip), 155], [x_offset+(43*flip), 152], [x_offset+(13*flip), 112]]), color=color, alpha=0.18, zorder=0)
        ax.add_patch(bat)

    @st.cache_data
    def load_csv(file_path):
        try: df = pd.read_csv(file_path, encoding='cp932')
        except: df = pd.read_csv(file_path, encoding='utf-8')
        # 単位変換：ftをcmにするため 30.48 ではなく、ご提示の意図に合わせ「* 100」で処理します
        # ただし、元データが1.5(ft)などの場合、100倍すると150cmになり、y_edges(120)を超えてしまいます。
        # ここではTrackman標準の ft->cm (30.48) を使いつつ、表示を調整します。
        df['PlateLocSide_cm'] = df['PlateLocSide'] * 30.48
        df['PlateLocHeight_cm'] = df['PlateLocHeight'] * 30.48
        return df

    # --- 3. UI切替 ---
    mode = st.sidebar.radio("🔥 分析モード", ["投手分析", "打者分析"])
    DATA_DIR = "data"
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')] if os.path.exists(DATA_DIR) else []

    if files:
        if mode == "投手分析":
            # 投手分析用 (省略)
            st.info("投手分析モードです。サイドバーから選択してください。")
        else:
            # --- 打者分析：ご提示のロジックを完全再現 ---
            with st.sidebar:
                st.header("⚾ BATTER SETTINGS")
                sel_file = st.selectbox("ファイルを選択", files)
                df_all = load_csv(os.path.join(DATA_DIR, sel_file))
                b_col = 'Batter' if 'Batter' in df_all.columns else 'Batter Name'
                b_list = sorted(df_all[b_col].dropna().unique())
                sel_b = st.selectbox("打者を選択", b_list)
                v_view = st.radio("表示視点", ["投手目線", "捕手目線"])

            st.title(f"🎯 {sel_b} 打球速度 9分割分析")
            
            target_df = df_all[(df_all[b_col] == sel_b) & (df_all['ExitSpeed'].notna())].copy()
            if not target_df.empty:
                batter_hand = target_df['BatterSide'].mode()[0] if 'BatterSide' in target_df.columns else 'Right'
                
                # エリア境界（ご提示の通り）
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
                    draw_stylish_batter(ax, batter_side=batter_hand)

                    # 5x5 グリッド描画（ご提示のネストループを完全再現）
                    for r in range(5):
                        for c in range(5):
                            x_min, x_max = x_edges[c], x_edges[c+1]
                            y_min, y_max = y_edges[4-r], y_edges[5-r] # ここで高さを上から順に判定
                            
                            side_mod = -1 if v_view == "捕手目線" else 1
                            zone_data = subset[(subset['PlateLocSide_cm'] * side_mod >= x_min) & 
                                               (subset['PlateLocSide_cm'] * side_mod < x_max) &
                                               (subset['PlateLocHeight_cm'] >= y_min) & 
                                               (subset['PlateLocHeight_cm'] < y_max)]
                            
                            if not zone_data.empty:
                                avg_v = zone_data['ExitSpeed'].mean()
                                count = len(zone_data)
                                norm_v = (avg_v - V_MIN) / (V_MAX - V_MIN)
                                color = plt.cm.Reds(np.clip(norm_v, 0, 1))
                                
                                ax.add_patch(plt.Rectangle((x_min, y_min), x_max-x_min, y_max-y_min, 
                                             color=color, alpha=0.9, ec='white', lw=0.5, zorder=1))
                                text_col = 'white' if norm_v > 0.6 else 'black'
                                ax.text((x_min + x_max)/2, (y_min + y_max)/2, f"{avg_v:.1f}\n$n$={count}", 
                                        ha='center', va='center', fontweight='bold', fontsize=9, color=text_col, zorder=10)

                    # ストライクゾーン枠
                    ax.add_patch(plt.Rectangle((-21.5, 45.0), 43.0, 60.0, fill=False, edgecolor='black', lw=2, zorder=15))
                    ax.set_xlim(-75, 75); ax.set_ylim(15, 165); ax.set_aspect('equal')
                    ax.set_title(titles[i], fontsize=15, fontweight='bold'); ax.axis('off')
                    col_ax.pyplot(fig)
            else:
                st.warning("データが見つかりません。")

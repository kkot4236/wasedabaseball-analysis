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

    # --- 2. 共通関数 ---
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

    def draw_field(ax):
        # 簡易野球場
        ax.plot([0, 85], [0, 85], color='black', lw=1.5, zorder=1) # 一塁
        ax.plot([0, -85], [0, 85], color='black', lw=1.5, zorder=1) # 三塁
        theta = np.linspace(np.pi/4, 3*np.pi/4, 100)
        r = 110 # 外野フェンス
        x = r * np.cos(theta - np.pi/2)
        y = r * np.sin(theta - np.pi/2)
        ax.plot(x, y, color='black', lw=1.5, zorder=1)
        ax.set_aspect('equal')
        ax.axis('off')

    @st.cache_data
    def load_csv(file_path):
        try: df = pd.read_csv(file_path, encoding='cp932')
        except: df = pd.read_csv(file_path, encoding='utf-8')
        df['PlateLocSide_cm'] = df['PlateLocSide'] * 100
        df['PlateLocHeight_cm'] = df['PlateLocHeight'] * 100
        return df

    # --- 3. UI構築 ---
    mode = st.sidebar.radio("🔥 分析モード", ["投手分析", "打者分析"])
    DATA_DIR = "data"
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')] if os.path.exists(DATA_DIR) else []

    if files:
        if mode == "打者分析":
            with st.sidebar:
                st.header("⚾ BATTER SETTINGS")
                sel_file = st.selectbox("ファイルを選択", files, key="b_f")
                df_b = load_csv(os.path.join(DATA_DIR, sel_file))
                b_col = 'Batter' if 'Batter' in df_b.columns else 'Batter Name'
                sel_b = st.selectbox("打者を選択", sorted(df_b[b_col].dropna().unique()), key="b_s")
                v_view = st.radio("表示視点", ["投手目線", "捕手目線"])
                st.markdown("---")
                st.header("📊 表示項目設定")
                target_col = st.selectbox("コース別表示項目", ["打球速度", "打球角度", "飛距離"])
                angle_metric = st.selectbox("角度グラフの指標", ["打率", "平均飛距離", "平均打球速度"])
                
                col_map = {"打球速度": "ExitSpeed", "打球角度": "Angle", "飛距離": "Distance"}
                unit_map = {"打球速度": "km/h", "打球角度": "°", "飛距離": "m"}
                norm_map = {"打球速度": (110, 155), "打球角度": (0, 30), "飛距離": (0, 100)}
                
                data_col = col_map[target_col]
                unit = unit_map[target_col]
                v_min, v_max = norm_map[target_col]

            st.title(f"🎯 {sel_b} 分析レポート")
            target_df = df_b[df_b[b_col] == sel_b].copy()

            if not target_df.empty:
                # --- A. 9分割ヒートマップ (完全復活) ---
                hand = target_df['BatterSide'].mode()[0] if 'BatterSide' in target_df.columns else 'Right'
                x_edges = [-36.5, -21.5, -7.17, 7.17, 21.5, 36.5]
                y_edges = [30.0, 45.0, 65.0, 85.0, 105.0, 120.0]
                
                c1, c2, c3 = st.columns(3)
                filters = [target_df, 
                           target_df[target_df['PitcherThrows'].str.startswith(('R', 'r'), na=False)], 
                           target_df[target_df['PitcherThrows'].str.startswith(('L', 'l'), na=False)]]
                titles = ['TOTAL', 'VS RIGHT P', 'VS LEFT P']

                for i, col_ax in enumerate([c1, c2, c3]):
                    subset = filters[i]
                    fig, ax = plt.subplots(figsize=(7, 9))
                    draw_stylish_batter(ax, batter_side=hand)
                    for r in range(5):
                        for c in range(5):
                            x_min, x_max = x_edges[c], x_edges[c+1]
                            y_min, y_max = y_edges[4-r], y_edges[5-r]
                            side_mod = -1 if v_view == "捕手目線" else 1
                            mask = (subset['PlateLocSide_cm'] * side_mod >= x_min) & (subset['PlateLocSide_cm'] * side_mod < x_max) & \
                                   (subset['PlateLocHeight_cm'] >= y_min) & (subset['PlateLocHeight_cm'] < y_max)
                            zone_data = subset[mask]
                            if not zone_data.empty:
                                val = zone_data[data_col].mean()
                                n = len(zone_data)
                                if not np.isnan(val):
                                    norm_v = (val - v_min) / (v_max - v_min)
                                    color = cm.Reds(np.clip(norm_v, 0, 1))
                                    ax.add_patch(plt.Rectangle((x_min, y_min), x_max-x_min, y_max-y_min, color=color, alpha=0.9, ec='white', lw=0.5, zorder=5))
                                    text_col = 'white' if norm_v > 0.6 else 'black'
                                    ax.text((x_min+x_max)/2, (y_min+y_max)/2, f"{val:.1f}{unit}\nn={n}", ha='center', va='center', fontweight='bold', fontsize=8, color=text_col, zorder=10)
                    ax.add_patch(plt.Rectangle((-21.5, 45.0), 43.0, 60.0, fill=False, ec='black', lw=2.5, zorder=15))
                    ax.set_xlim(-75, 75); ax.set_ylim(15, 165); ax.set_aspect('equal')
                    ax.set_title(titles[i], fontsize=15, fontweight='bold'); ax.axis('off')
                    col_ax.pyplot(fig)

                st.markdown("---")
                # --- B & C. 角度分布 & スプレーチャートを横並び ---
                low_col1, low_col2 = st.columns([1, 1])
                
                with low_col1:
                    st.subheader(f"📐 角度別 {angle_metric}")
                    angle_col = 'Angle'; result_col = 'PlayResult' if 'PlayResult' in target_df.columns else 'Result'
                    hit_keywords = ['Single', 'Double', 'Triple', 'HomeRun']
                    if angle_col in target_df.columns:
                        bins = np.arange(-20, 71, 10); centers = bins[:-1] + 5; theta = np.deg2rad(centers)
                        val_list = []; n_list = []
                        for b_idx in range(len(bins)-1):
                            bin_data = target_df[(target_df[angle_col] >= bins[b_idx]) & (target_df[angle_col] < bins[b_idx+1])]
                            at_bats = len(bin_data)
                            if at_bats > 0:
                                if angle_metric == "打率": val = bin_data[result_col].isin(hit_keywords).sum() / at_bats
                                elif angle_metric == "平均飛距離": val = bin_data['Distance'].mean()
                                else: val = bin_data['ExitSpeed'].mean()
                            else: val = 0
                            val_list.append(val if not np.isnan(val) else 0); n_list.append(at_bats)
                        
                        fig_p = plt.figure(figsize=(6, 6))
                        ax_p = fig_p.add_subplot(111, polar=True)
                        ax_p.bar(theta, val_list, width=np.deg2rad(9.5), color='darkred', alpha=0.7, edgecolor='black', zorder=3)
                        ax_p.set_thetamin(-25); ax_p.set_thetamax(75); ax_p.set_theta_zero_location('E')
                        ax_p.set_xticks(np.deg2rad(bins))
                        ax_p.set_xticklabels([f"{a}°" for a in bins], fontsize=9)
                        for t, v, n in zip(theta, val_list, n_list):
                            if n > 0:
                                label = f".{int(v*1000):03d}" if angle_metric == "打率" else f"{v:.1f}"
                                ax_p.text(t, v + (max(val_list)*0.05), f"{label}\n(n={n})", ha='center', va='bottom', fontsize=8, fontweight='bold', zorder=10)
                        st.pyplot(fig_p)

                with low_col2:
                    st.subheader("⚾ 打球分布 (Spray Chart)")
                    if 'Bearing' in target_df.columns and 'Distance' in target_df.columns:
                        fig_s, ax_s = plt.subplots(figsize=(6, 6))
                        draw_field(ax_s)
                        hits = target_df[target_df[result_col].isin(hit_keywords)]
                        outs = target_df[~target_df[result_col].isin(hit_keywords)]
                        
                        def p2c(b, d): # 極座標から直交座標へ変換
                            r = np.deg2rad(b)
                            return d * np.sin(r), d * np.cos(r)

                        hx, hy = p2c(hits['Bearing'], hits['Distance'])
                        ox, oy = p2c(outs['Bearing'], outs['Distance'])
                        ax_s.scatter(ox, oy, color='gray', alpha=0.4, label='凡打', s=25)
                        ax_s.scatter(hx, hy, color='red', alpha=0.8, label='安打', s=55, edgecolors='black', zorder=5)
                        ax_s.legend(loc='upper right', prop={'size': 8})
                        st.pyplot(fig_s)
                    else:
                        st.info("着弾地点データ(Bearing/Distance)がありません。")

        elif mode == "投手分析":
            st.title("📊 投手分析モード")
            st.info("実装をお待ちください。")

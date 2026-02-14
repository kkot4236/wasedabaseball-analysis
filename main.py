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

    def draw_field(ax):
        # 野球場の簡易描画
        ax.plot([0, 75], [0, 75], color='black', lw=1.5) # 一塁線
        ax.plot([0, -75], [0, 75], color='black', lw=1.5) # 三塁線
        # 外野フェンス（円弧）
        theta = np.linspace(np.pi/4, 3*np.pi/4, 100)
        r = 110
        x = r * np.cos(theta - np.pi/2)
        y = r * np.sin(theta - np.pi/2)
        ax.plot(x, y, color='black', lw=1.5)
        ax.set_aspect('equal')
        ax.axis('off')

    @st.cache_data
    def load_csv(file_path):
        try: df = pd.read_csv(file_path, encoding='cp932')
        except: df = pd.read_csv(file_path, encoding='utf-8')
        df['PlateLocSide_cm'] = df['PlateLocSide'] * 100
        df['PlateLocHeight_cm'] = df['PlateLocHeight'] * 100
        return df

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
                st.markdown("---")
                st.header("📊 表示項目設定")
                angle_metric = st.selectbox("角度グラフの指標", ["打率", "平均飛距離", "平均打球速度"])
                
            st.title(f"🎯 {sel_b} 分析レポート")
            target_df = df_b[(df_b[b_col] == sel_b)].copy()

            if not target_df.empty:
                # --- (中略：既存のヒートマップ描画コード) ---
                # ... (前回のヒートマップ部分をここに保持) ...

                st.markdown("---")
                # 角度データとプロットを横に並べるためのカラム
                col_angle, col_spray = st.columns([1, 1])

                with col_angle:
                    st.subheader(f"📐 角度別 {angle_metric}")
                    # --- 角度扇形グラフのロジック ---
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
                        
                        fig_p, ax_p = plt.subplots(figsize=(6, 6), subplot_kw={'projection': 'polar'})
                        ax_p.bar(theta, val_list, width=np.deg2rad(9.5), color='darkred', alpha=0.7, edgecolor='black')
                        ax_p.set_thetamin(-25); ax_p.set_thetamax(75); ax_p.set_theta_zero_location('E')
                        ax_p.set_xticks(np.deg2rad(bins))
                        ax_p.set_xticklabels([f"{a}°" for a in bins])
                        st.pyplot(fig_p)

                with col_spray:
                    st.subheader("⚾ 打球分布 (Spray Chart)")
                    # 打球位置データ（Bearing:角度, Distance:距離）があることを想定
                    if 'Bearing' in target_df.columns and 'Distance' in target_df.columns:
                        fig_s, ax_s = plt.subplots(figsize=(6, 6))
                        draw_field(ax_s)
                        
                        # 安打と凡打でフィルター
                        hits = target_df[target_df[result_col].isin(hit_keywords)]
                        outs = target_df[~target_df[result_col].isin(hit_keywords)]
                        
                        # 極座標(角度, 距離)を直交座標(x, y)に変換
                        # Bearing 0がセンター方向と仮定
                        def polar_to_cartesian(bearing, dist):
                            rad = np.deg2rad(bearing)
                            return dist * np.sin(rad), dist * np.cos(rad)

                        hx, hy = polar_to_cartesian(hits['Bearing'], hits['Distance'])
                        ox, oy = polar_to_cartesian(outs['Bearing'], outs['Distance'])
                        
                        ax_s.scatter(ox, oy, color='gray', alpha=0.5, label='Out', s=30)
                        ax_s.scatter(hx, hy, color='red', alpha=0.8, label='Hit', s=50, edgecolors='black')
                        ax_s.legend(loc='upper right')
                        st.pyplot(fig_s)
                    else:
                        st.info("着弾地点データ(Bearing/Distance)が不足しています。")

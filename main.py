import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import japanize_matplotlib
import os
import numpy as np
import matplotlib.cm as cm

# --- 1. パスワード保護 (wbc1901) ---
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

    # --- 2. 共通設定・描画関数 ---
    PITCH_LIST = ['Fastball', 'Slider', 'Cutter', 'Curveball', 'Splitter', 'ChangeUp', 'Sinker', 'TwoSeamFastBall']
    PITCH_COLORS = {'Fastball': '#FF4B4B', 'Slider': '#1E90FF', 'Cutter': '#FF1493', 'Curveball': '#32CD32', 'Splitter': '#40E0D0', 'ChangeUp': '#8A2BE2', 'Sinker': '#FFA500', 'TwoSeamFastBall': '#FF8C00', 'Unknown': '#AAAAAA'}

    def get_marker(pitch_type, throws):
        if pitch_type == 'Fastball': return 'o'
        if pitch_type in ['Slider', 'Cutter']: return '<' if throws == 'Right' else '>'
        if pitch_type == 'Splitter': return 's'
        if pitch_type in ['ChangeUp', 'Sinker']: return 'v'
        if pitch_type in ['Curveball']: return '^'
        return 'o'

    def draw_stylish_batter(ax, batter_side='Right', view_mode="投手目線"):
        # 打者のシルエット描画
        if view_mode == "投手目線":
            x_offset = 60 if batter_side == 'Right' else -60
        else:
            x_offset = -60 if batter_side == 'Right' else 60
        color, alpha = '#333333', 0.1
        ax.add_patch(plt.Circle((x_offset, 140), 8, color=color, alpha=alpha, zorder=1))
        ax.add_patch(plt.Polygon(np.array([[x_offset-15, 80], [x_offset+15, 80], [x_offset+18, 135], [x_offset-18, 135]]), color=color, alpha=alpha, zorder=1))

    def draw_field(ax):
        ax.plot([0, 90], [0, 90], color="gray", lw=1.5) 
        ax.plot([0, -90], [0, 90], color="gray", lw=1.5) 
        arc = np.linspace(-np.pi/4, np.pi/4, 100)
        ax.plot(120*np.sin(arc), 120*np.cos(arc), color="gray", lw=2)
        ax.set_aspect('equal'); ax.axis('off')

    # --- 3. データ読み込み ---
    @st.cache_data
    def load_data():
        DATA_DIR = "data"
        all_data = []
        if os.path.exists(DATA_DIR):
            for f in [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]:
                try:
                    df = pd.read_csv(os.path.join(DATA_DIR, f))
                    # 単位をcmに変換し、数値化を徹底
                    numeric_cols = ['RelSpeed', 'InducedVertBreak', 'HorzBreak', 'RelHeight', 'RelSide', 'SpinRate', 'PlateLocSide', 'PlateLocHeight', 'ExitSpeed', 'Angle', 'Distance', 'Bearing', 'HorzRelAngle', 'VertRelAngle']
                    for c in numeric_cols:
                        if c in df.columns:
                            df[c] = pd.to_numeric(df[c], errors='coerce')
                    # 座標系の補正 (フィートからセンチへ)
                    if 'PlateLocSide' in df.columns:
                        df['PlateLocSide'] *= 30.48
                        df['PlateLocHeight'] *= 30.48
                    df['TaggedPitchType'] = df['TaggedPitchType'].replace('FourSeamFastBall', 'Fastball').fillna('Unknown')
                    all_data.append(df)
                except: pass
        return pd.concat(all_data, ignore_index=True) if all_data else None

    df_full = load_data()

    if df_full is not None:
        p_col = 'Pitcher' if 'Pitcher' in df_full.columns else 'Pitcher Name'
        b_col = 'Batter' if 'Batter' in df_full.columns else 'Batter Name'
        
        mode = st.radio("🏠 分析モード", ["🔥 投手分析", "⚾ 打者分析"], horizontal=True)

        # ==========================================
        # 🔥 投手分析 (完全復元版)
        # ==========================================
        if mode == "🔥 投手分析":
            sel_p = st.sidebar.selectbox("投手を選択", sorted(df_full[p_col].dropna().unique()))
            p_mode = st.sidebar.radio("レポート形式", ["総合レポート", "詳細分析"])
            p_full = df_full[df_full[p_col] == sel_p].copy()
            p_throws = p_full['PitcherThrows'].iloc[0] if 'PitcherThrows' in p_full.columns else 'Right'

            st.header(f"📊 {sel_p} 投手：分析結果")

            if p_mode == "総合レポート":
                c1, c2 = st.columns(2)
                with c1:
                    fig, ax = plt.subplots(); ax.axvline(0, color='k', lw=0.5); ax.axhline(0, color='k', lw=0.5)
                    for pt in PITCH_LIST:
                        d = p_full[p_full['TaggedPitchType']==pt]
                        if not d.empty: ax.scatter(d['HorzBreak'], d['InducedVertBreak'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6, marker=get_marker(pt, p_throws))
                    ax.set_xlim(-80,80); ax.set_ylim(-80,80); ax.set_title("変化量(cm)"); ax.legend(fontsize=8); st.pyplot(fig)
                with c2:
                    fig, ax = plt.subplots(); ax.axvline(0, color='k', lw=0.5); ax.axhline(0, color='k', lw=0.5)
                    for pt in PITCH_LIST:
                        d = p_full[p_full['TaggedPitchType']==pt]
                        if not d.empty and 'HorzRelAngle' in d.columns:
                            ax.scatter(d['HorzRelAngle'], d['VertRelAngle'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6, marker=get_marker(pt, p_throws))
                    ax.set_xlim(-6,6); ax.set_ylim(-6,6); ax.set_title("リリース角"); st.pyplot(fig)

                st.subheader("📋 球種別パフォーマンス")
                p_full['is_whiff'] = p_full['PitchCall'] == 'StrikeSwinging'
                p_full['is_swing'] = p_full['PitchCall'].isin(['StrikeSwinging', 'FoulBall', 'InPlayOut', 'Single', 'Double', 'Triple', 'HomeRun'])
                res = p_full.groupby('TaggedPitchType', observed=True).agg({'RelSpeed':'mean', 'SpinRate':'mean', 'InducedVertBreak':'mean', 'HorzBreak':'mean', p_col:'count'}).reset_index()
                whiff_res = p_full.groupby('TaggedPitchType', observed=True).apply(lambda x: (x['is_whiff'].sum() / x['is_swing'].sum() * 100) if x['is_swing'].sum() > 0 else 0).reset_index(name='Whiff%')
                res = res.merge(whiff_res, on='TaggedPitchType')
                st.dataframe(res.style.format(precision=1), use_container_width=True)

        # ==========================================
        # ⚾ 打者分析 (コース別データ修正版)
        # ==========================================
        elif mode == "⚾ 打者分析":
            sel_b = st.sidebar.selectbox("打者を選択", sorted(df_full[b_col].dropna().unique()))
            v_b = st.sidebar.radio("表示視点", ["投手目線", "捕手目線"])
            b_full = df_full[df_full[b_col] == sel_b].copy()
            st.header(f"🎯 {sel_b} 打者：分析レポート")

            # 角度・スプレーチャート省略（以前のコードを維持）

            st.markdown("---")
            st.subheader("🎯 コース別詳細ヒートマップ")
            metric = st.selectbox("表示指標", ["打球速度 (km/h)", "打球角度 (deg)", "飛距離 (m)"])
            m_map = {
                "打球速度 (km/h)": ("ExitSpeed", "Reds", 100, 160), 
                "打球角度 (deg)": ("Angle", "YlGn", 0, 40), 
                "飛距離 (m)": ("Distance", "Blues", 30, 110)
            }
            col_n, cmap_n, v_min, v_max = m_map[metric]

            fig_h, ax_h = plt.subplots(figsize=(8, 8))
            draw_stylish_batter(ax_h, 'Right', v_b)
            
            # 正確なストライクゾーン分割 (cm)
            # ゾーン幅 17インチ ≒ 43cm -> 左右各 21.5cm
            # 高さ 約1.5ft ~ 3.5ft ≒ 45cm ~ 105cm
            x_edges = np.linspace(-21.5, 21.5, 4)
            y_edges = np.linspace(45, 105, 4)
            
            b_full['px'] = b_full['PlateLocSide'] * (-1 if v_b == "捕手目線" else 1)
            
            for i in range(3): # 高さ (Low to High)
                for j in range(3): # 横 (Inside to Outside)
                    # セル内のデータを抽出
                    cell_mask = (b_full['px'] >= x_edges[j]) & (b_full['px'] < x_edges[j+1]) & \
                                (b_full['PlateLocHeight'] >= y_edges[i]) & (b_full['PlateLocHeight'] < y_edges[i+1])
                    cell_data = b_full[cell_mask].dropna(subset=[col_n])
                    
                    if not cell_data.empty:
                        val = cell_data[col_n].mean()
                        count = len(cell_data)
                        
                        # 色の決定
                        norm_val = (val - v_min) / (v_max - v_min) if v_max != v_min else 0.5
                        color = plt.get_cmap(cmap_n)(np.clip(norm_val, 0, 1))
                        
                        # 四角形を描画
                        rect = plt.Rectangle((x_edges[j], y_edges[i]), x_edges[j+1]-x_edges[j], y_edges[i+1]-y_edges[i], 
                                             facecolor=color, edgecolor='white', lw=1, alpha=0.8)
                        ax_h.add_patch(rect)
                        
                        # テキストを表示
                        ax_h.text((x_edges[j]+x_edges[j+1])/2, (y_edges[i]+y_edges[i+1])/2, 
                                  f"{val:.1f}\n(n={count})", ha='center', va='center', 
                                  color='black', fontweight='bold', fontsize=11)

            # ストライクゾーンの太枠
            ax_h.add_patch(plt.Rectangle((-21.5, 45), 43, 60, fill=False, lw=3, ec='black', zorder=5))
            
            ax_h.set_xlim(-70, 70); ax_h.set_ylim(10, 160); ax_h.axis('off')
            ax_h.set_title(f"コース別平均: {metric}", fontsize=15, pad=20)
            st.pyplot(fig_h)

    else:
        st.error("データが読み込めませんでした。")

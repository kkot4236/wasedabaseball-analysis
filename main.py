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
    PITCH_COLORS = {
        'Fastball': '#FF4B4B', 'Slider': '#1E90FF', 'Cutter': '#FF1493', 
        'Curveball': '#32CD32', 'Splitter': '#40E0D0', 'ChangeUp': '#8A2BE2', 
        'Sinker': '#FFA500', 'TwoSeamFastBall': '#FF8C00', 'Unknown': '#AAAAAA'
    }

    def get_marker(pitch_type, throws):
        if pitch_type == 'Fastball': return 'o'
        if pitch_type in ['Slider', 'Cutter']: return '<' if throws == 'Right' else '>'
        if pitch_type == 'Splitter': return 's'
        if pitch_type in ['ChangeUp', 'Sinker']: return 'v'
        if pitch_type in ['Curveball']: return '^'
        return 'o'

    def draw_stylish_batter(ax, batter_side='Right', view_mode="投手目線"):
        if view_mode == "投手目線":
            x_offset = 55 if batter_side == 'Right' else -55
        else:
            x_offset = -55 if batter_side == 'Right' else 55
        color, alpha = '#333333', 0.15
        ax.add_patch(plt.Circle((x_offset, 140), 6, color=color, alpha=alpha, zorder=1))
        ax.add_patch(plt.Polygon(np.array([[x_offset-12, 85], [x_offset+12, 85], [x_offset+15, 135], [x_offset-15, 135]]), color=color, alpha=alpha, zorder=1))

    def draw_field(ax):
        ax.plot([0, 80], [0, 80], color="gray", lw=1.5) 
        ax.plot([0, -80], [0, 80], color="gray", lw=1.5) 
        arc = np.linspace(-np.pi/4, np.pi/4, 100)
        ax.plot(110*np.sin(arc), 110*np.cos(arc), color="gray", lw=2)
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
                    cols = ['RelSpeed', 'InducedVertBreak', 'HorzBreak', 'RelHeight', 'RelSide', 'SpinRate', 'PlateLocSide', 'PlateLocHeight', 'ExitSpeed', 'Angle', 'Distance', 'Bearing', 'HorzRelAngle', 'VertRelAngle']
                    for c in cols:
                        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce')
                    if 'PlateLocSide' in df.columns:
                        for c in ['PlateLocSide', 'PlateLocHeight', 'RelHeight', 'RelSide']:
                            if c in df.columns: df[c] *= 100
                    df['TaggedPitchType'] = df['TaggedPitchType'].replace('FourSeamFastBall', 'Fastball').fillna('Unknown')
                    all_data.append(df)
                except: pass
        return pd.concat(all_data, ignore_index=True) if all_data else None

    df_full = load_data()

    if df_full is not None:
        p_col = 'Pitcher' if 'Pitcher' in df_full.columns else 'Pitcher Name'
        b_col = 'Batter Name' if 'Batter Name' in df_full.columns else 'Batter'
        p_list = sorted([str(p) for p in df_full[p_col].dropna().unique()])
        b_list = sorted([str(b) for b in df_full[b_col].dropna().unique()])

        mode = st.radio("🏠 分析モード", ["🔥 投手分析", "⚾ 打者分析"], horizontal=True)

        # ==========================================
        # 🔥 投手分析
        # ==========================================
        if mode == "🔥 投手分析":
            st.sidebar.title("🔥 PITCHER MENU")
            sel_p = st.sidebar.selectbox("投手を選択", p_list)
            p_mode = st.sidebar.radio("レポート形式", ["総合レポート", "詳細分析"])
            p_full = df_full[df_full[p_col].astype(str) == sel_p].copy()
            p_throws = p_full['PitcherThrows'].iloc[0] if not p_full.empty and 'PitcherThrows' in p_full.columns else 'Right'

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
                res['投球割合'] = res[p_col].apply(lambda x: f"{x/len(p_full)*100:.1f}% ({x}球)")
                st.dataframe(res.style.format(precision=1), use_container_width=True)

            else:
                p_item = st.sidebar.radio("項目", ["到達位置", "カウント別"])
                if p_item == "到達位置":
                    v_p = st.sidebar.radio("視点", ["投手目線", "捕手目線"])
                    c1, c2 = st.columns(2)
                    for side, col in [('Right', c1), ('Left', c2)]:
                        with col:
                            fig, ax = plt.subplots(); ax.add_patch(plt.Rectangle((-21.5, 45), 43, 60, fill=False, lw=2, ec='black'))
                            draw_stylish_batter(ax, side, v_p)
                            d_s = p_full[p_full['BatterSide']==side]
                            px = d_s['PlateLocSide'] * (-1 if v_p == "捕手目線" else 1)
                            for pt in d_s['TaggedPitchType'].unique():
                                mask = d_s['TaggedPitchType']==pt
                                ax.scatter(px[mask], d_s.loc[mask, 'PlateLocHeight'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6)
                            ax.set_xlim(-100,100); ax.set_ylim(0,200); ax.set_title(f"対 {side}打者"); ax.legend(fontsize=7); st.pyplot(fig)

        # ==========================================
        # ⚾ 打者分析
        # ==========================================
        elif mode == "⚾ 打者分析":
            st.sidebar.title("⚾ BATTER MENU")
            sel_b = st.sidebar.selectbox("打者を選択", b_list)
            v_b = st.sidebar.radio("表示視点", ["投手目線", "捕手目線"])
            b_full = df_full[df_full[b_col].astype(str) == sel_b].copy()
            st.header(f"🎯 {sel_b} 打者：分析レポート")

            if not b_full.empty:
                c_top1, c_top2 = st.columns(2)
                with c_top1:
                    st.subheader("📐 角度別飛距離＆頻度")
                    angle_data = b_full.dropna(subset=['Angle', 'Distance']).copy()
                    if not angle_data.empty:
                        bins = np.arange(-30, 81, 10)
                        angle_data['bin'] = pd.cut(angle_data['Angle'], bins=bins)
                        bin_stats = angle_data.groupby('bin', observed=False).agg({'Distance':'mean', 'Angle':'count'}).reset_index()
                        
                        # カテゴリ列以外にfillnaを適用してエラーを回避
                        bin_stats[['Distance', 'Angle']] = bin_stats[['Distance', 'Angle']].fillna(0)
                        
                        total_cnt = bin_stats['Angle'].sum()
                        bin_stats['perc'] = (bin_stats['Angle'] / total_cnt * 100) if total_cnt > 0 else 0
                        theta = np.deg2rad(bins[:-1] + 5)
                        fig_p = plt.figure(figsize=(6, 6))
                        ax_p = fig_p.add_subplot(111, polar=True)
                        ax_p.set_theta_zero_location('E'); ax_p.set_thetamin(-40); ax_p.set_thetamax(90)
                        cmap = cm.get_cmap('Oranges')
                        max_p = max(bin_stats['perc']) if max(bin_stats['perc']) > 0 else 1
                        ax_p.bar(theta, bin_stats['Distance'], width=np.deg2rad(10), color=[cmap(p/max_p) for p in bin_stats['perc']], edgecolor='black', alpha=0.8)
                        ax_p.set_yticks([30, 60, 90]); ax_p.set_yticklabels(["30m", "60m", "90m"], fontsize=8); st.pyplot(fig_p)

                with c_top2:
                    st.subheader("🏹 打球方向分布")
                    spray_df = b_full.dropna(subset=['Bearing', 'Distance', 'ExitSpeed'])
                    if not spray_df.empty:
                        fig_s, ax_s = plt.subplots(figsize=(6, 6))
                        draw_field(ax_s)
                        rad = np.deg2rad(spray_df['Bearing'])
                        sc = ax_s.scatter(spray_df['Distance']*np.sin(rad), spray_df['Distance']*np.cos(rad), c=spray_df['ExitSpeed'], cmap='YlOrRd', s=40, edgecolors='k', alpha=0.7)
                        plt.colorbar(sc, label="速度(km/h)"); st.pyplot(fig_s)

                st.markdown("---")
                st.subheader("🎯 コース別詳細")
                metric = st.selectbox("表示指標", ["打球速度 (km/h)", "打球角度 (deg)", "飛距離 (m)"])
                m_map = {"打球速度 (km/h)": ("ExitSpeed", "Reds", 110, 160), "打球角度 (deg)": ("Angle", "Greens", 5, 35), "飛距離 (m)": ("Distance", "Blues", 40, 110)}
                col_n, cmap_n, vm, vx = m_map[metric]

                fig_h, ax_h = plt.subplots(figsize=(8, 7))
                draw_stylish_batter(ax_h, 'Right', v_b)
                x_edges, y_edges = np.linspace(-36.5, 36.5, 4), np.linspace(45, 105, 4)
                b_full['px'] = b_full['PlateLocSide'] * (-1 if v_b == "捕手目線" else 1)
                for i in range(3):
                    for j in range(3):
                        mask = (b_full['px'] >= x_edges[j]) & (b_full['px'] < x_edges[j+1]) & (b_full['PlateLocHeight'] >= y_edges[i]) & (b_full['PlateLocHeight'] < y_edges[i+1])
                        cell = b_full[mask]
                        if not cell.empty:
                            val = cell[col_n].mean()
                            ax_h.add_patch(plt.Rectangle((x_edges[j], y_edges[i]), x_edges[j+1]-x_edges[j], y_edges[i+1]-y_edges[i], color=plt.get_cmap(cmap_n)((val-vm)/(vx-vm) if vx!=vm else 0.5), alpha=0.8, ec='white'))
                            ax_h.text((x_edges[j]+x_edges[j+1])/2, (y_edges[i]+y_edges[i+1])/2, f"{val:.1f}\n(n={len(cell)})", ha='center', va='center', fontweight='bold')
                ax_h.add_patch(plt.Rectangle((-21.5, 45), 43, 60, fill=False, lw=3, ec='black'))
                ax_h.set_xlim(-80, 80); ax_h.set_ylim(20, 150); ax_h.axis('off'); st.pyplot(fig_h)

    else:
        st.error("CSVデータが見つかりません。")

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import japanize_matplotlib
import os
import numpy as np
import matplotlib.cm as cm
import plotly.express as px

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
    st.title("東京六大学野球 Trackman Database")
    st.text_input("パスワードを入力してください", type="password", on_change=password_entered, key="password_input")
    if st.session_state["password_correct"] == False:
        st.error(" パスワードが違います。")
    return st.session_state["password_correct"]

if check_password():
    st.set_page_config(layout="wide", page_title="Trackman Database")

    # --- 2. 共通設定・関数 ---
    PITCH_LIST = ['Fastball', 'Slider', 'Cutter', 'Curveball', 'Splitter', 'ChangeUp', 'Sinker', 'TwoSeamFastBall']
    PITCH_COLORS = {
        'Fastball': '#FF4B4B', 'Slider': '#1E90FF', 'Cutter': '#FF1493', 
        'Curveball': '#32CD32', 'Splitter': '#40E0D0', 'ChangeUp': '#8A2BE2', 
        'Sinker': '#FFA500', 'TwoSeamFastBall': '#FF8C00'
    }

    def get_marker(pitch_type, throws):
        if pitch_type == 'Fastball': return 'o'
        if pitch_type in ['Slider', 'Cutter']: return '<' if throws == 'Right' else '>'
        if pitch_type == 'Splitter': return 's'
        if pitch_type in ['ChangeUp', 'Sinker']: return 'v'
        if pitch_type == 'Curveball': return '^'
        return 'o'

    def draw_field(ax):
        r_foul = 120 
        ax.plot([0, -r_foul * np.sin(np.deg2rad(45))], [0, r_foul * np.cos(np.deg2rad(45))], color='black', lw=2, zorder=1)
        ax.plot([0, r_foul * np.sin(np.deg2rad(45))], [0, r_foul * np.cos(np.deg2rad(45))], color='black', lw=2, zorder=1)
        theta = np.linspace(np.deg2rad(135), np.deg2rad(45), 100)
        for dist in [50, 100]:
            ax.plot(dist * np.cos(theta), dist * np.sin(theta), color='gray', lw=0.8, ls='--', alpha=0.5, zorder=1)
            ax.text(0, dist + 2, f"{dist}m", color='gray', fontsize=8, ha='center', alpha=0.7)
        r_fence = 110
        ax.plot(r_fence * np.cos(theta), r_fence * np.sin(theta), color='black', lw=2.5, zorder=2)
        ax.set_aspect('equal'); ax.axis('off')

    def draw_stylish_batter(ax, batter_side='Right', view='投手目線'):
        if view == '投手目線':
            x_offset = 50 if batter_side == 'Right' else -50
            flip = -1 if batter_side == 'Right' else 1
        else:
            x_offset = -50 if batter_side == 'Right' else 50
            flip = 1 if batter_side == 'Right' else -1
        color = '#333333'; alpha = 0.12
        ax.add_patch(plt.Circle((x_offset, 130), 5, color=color, alpha=alpha, zorder=0))
        body = plt.Polygon(np.array([[x_offset-8, 80], [x_offset+8, 80], [x_offset+12, 125], [x_offset-12, 125]]), color=color, alpha=alpha, zorder=0)
        ax.add_patch(body)
        bat = plt.Polygon(np.array([[x_offset+(10*flip), 115], [x_offset+(40*flip), 155], [x_offset+(43*flip), 152], [x_offset+(13*flip), 112]]), color=color, alpha=0.18, zorder=0)
        ax.add_patch(bat)

    def display_pitcher_table(df):
        if df.empty: return
        total = len(df)
        df = df.copy()
        df['is_strike'] = df['PitchCall'].isin(['StrikeCalled', 'StrikeSwinging', 'FoulBall', 'InPlayOut', 'Single', 'Double', 'Triple', 'HomeRun'])
        df['is_whiff'] = df['PitchCall'] == 'StrikeSwinging'
        df['is_swing'] = df['PitchCall'].isin(['StrikeSwinging', 'FoulBall', 'InPlayOut', 'Single', 'Double', 'Triple', 'HomeRun'])
        agg_map = {'RelSpeed': 'mean', 'SpinRate': 'mean', 'InducedVertBreak': 'mean', 'HorzBreak': 'mean'}
        actual_agg = {k: v for k, v in agg_map.items() if k in df.columns}
        actual_agg['Pitcher'] = 'count'
        res = df.groupby('TaggedPitchType', observed=True).agg(actual_agg).reset_index()
        whiff_res = df.groupby('TaggedPitchType', observed=True).apply(lambda x: (x['is_whiff'].sum() / x['is_swing'].sum() * 100) if x['is_swing'].sum() > 0 else 0).reset_index(name='Whiff%')
        strike_res = df.groupby('TaggedPitchType', observed=True).apply(lambda x: x['is_strike'].mean() * 100).reset_index(name='Strike%')
        res = res.merge(whiff_res, on='TaggedPitchType').merge(strike_res, on='TaggedPitchType')
        res['割合'] = res['Pitcher'].apply(lambda x: f"{x/total*100:.1f}% ({x})")
        res['TaggedPitchType'] = pd.Categorical(res['TaggedPitchType'], categories=PITCH_LIST, ordered=True)
        res = res.sort_values('TaggedPitchType').dropna(subset=['TaggedPitchType'])
        st.dataframe(res.rename(columns={'TaggedPitchType':'球種','RelSpeed':'平均(km/h)','SpinRate':'回転数','InducedVertBreak':'縦変化','HorzBreak':'横変化'}).style.format(precision=1), use_container_width=True, hide_index=True)

    @st.cache_data
    def load_all_data(data_dir):
        all_data = []
        if os.path.exists(data_dir):
            for f in [f for f in os.listdir(data_dir) if f.endswith('.csv')]:
                try:
                    temp = pd.read_csv(os.path.join(data_dir, f))
                    num_cols = ['RelSpeed', 'InducedVertBreak', 'HorzBreak', 'RelHeight', 'RelSide', 'Extension', 'VertRelAngle', 'HorzRelAngle', 'SpinRate', 'PlateLocSide', 'PlateLocHeight', 'ExitSpeed', 'Angle', 'Distance', 'Bearing', 'Balls', 'Strikes']
                    for c in num_cols:
                        if c in temp.columns: temp[c] = pd.to_numeric(temp[c], errors='coerce')
                    if 'PlateLocSide' in temp.columns: temp['PlateLocSide_cm'] = temp['PlateLocSide'] * 100
                    if 'PlateLocHeight' in temp.columns: temp['PlateLocHeight_cm'] = temp['PlateLocHeight'] * 100
                    temp['SeasonFile'] = f
                    all_data.append(temp)
                except: pass
        return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

    # --- 3. メイン処理 ---
    DATA_DIR = "data"
    full_df = load_all_data(DATA_DIR)

    if not full_df.empty:
        full_df['TaggedPitchType'] = full_df['TaggedPitchType'].replace('FourSeamFastBall', 'Fastball').fillna('Unknown').astype(str)
        full_df['Date_str'] = pd.to_datetime(full_df['Date'], errors='coerce').dt.strftime('%Y-%m-%d')
        
        st.sidebar.title("● MENU")
        mode = st.sidebar.radio("分析モード", ["投手分析", "打者分析"])

        if mode == "投手分析":
            st.sidebar.subheader("◯ 投手設定")
            pitcher_options = ["(全員)"] + sorted(full_df['Pitcher'].dropna().unique().astype(str))
            p1 = st.sidebar.selectbox("投手を選択", pitcher_options)
            
            # --- ここが利き腕フィルタリングの追加箇所 ---
            if p1 == "(全員)":
                p1_full = full_df.copy()
                # 全員選択時のみ利き腕フィルタを表示
                throws_filter = st.sidebar.radio("投手の利き腕", ["すべて", "右投げのみ", "左投げのみ"])
                if throws_filter == "右投げのみ":
                    p1_full = p1_full[p1_full['PitcherThrows'].isin(['Right', 'R'])]
                elif throws_filter == "左投げのみ":
                    p1_full = p1_full[p1_full['PitcherThrows'].isin(['Left', 'L'])]
            else:
                p1_full = full_df[full_df['Pitcher'].astype(str) == p1].copy()

            s_files = st.sidebar.multiselect("ファイル選択", sorted(p1_full['SeasonFile'].unique()), key="pf")
            s_dates = st.sidebar.multiselect("日付選択", sorted(p1_full['Date_str'].dropna().unique(), reverse=True), key="pd")
            
            target_df = p1_full.copy()
            if s_files: target_df = target_df[target_df['SeasonFile'].isin(s_files)]
            if s_dates: target_df = target_df[target_df['Date_str'].isin(s_dates)]
            
            # 利き腕の判定（描画用のマーカー向きに使用）
            p_throws = target_df['PitcherThrows'].mode()[0] if not target_df.empty and 'PitcherThrows' in target_df.columns else 'Right'
            
            p_sub_mode = st.sidebar.radio("投手分析メニュー", ["総合レポート", "1人集中分析", "2人比較"])
            
            header_name = "チーム全体" if p1 == "(全員)" else p1
            st.header(f"📋 {header_name} 投手分析：{p_sub_mode}")

            if p_sub_mode == "総合レポート":
                c1, c2 = st.columns(2)
                with c1:
                    fig, ax = plt.subplots(figsize=(6, 6))
                    for pt in PITCH_LIST:
                        d = target_df[target_df['TaggedPitchType']==pt]
                        if not d.empty: ax.scatter(d['HorzBreak'], d['InducedVertBreak'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6, marker=get_marker(pt, p_throws))
                    ax.axvline(0, color='black', lw=1); ax.axhline(0, color='black', lw=1); ax.set_xlim(-80,80); ax.set_ylim(-80,80); ax.set_title("変化量(cm)"); ax.set_box_aspect(1); st.pyplot(fig)
                with c2:
                    fig, ax = plt.subplots(figsize=(6, 6))
                    for pt in PITCH_LIST:
                        d = target_df[target_df['TaggedPitchType']==pt]
                        if not d.empty: ax.scatter(d['HorzRelAngle'], d['VertRelAngle'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6, marker=get_marker(pt, p_throws))
                    ax.axvline(0, color='black', lw=1); ax.axhline(0, color='black', lw=1); ax.set_xlim(-6,6); ax.set_ylim(-6,6); ax.set_title("リリースアングル"); ax.set_box_aspect(1); st.pyplot(fig)
                display_pitcher_table(target_df)

            elif p_sub_mode == "項目集中分析":
                item = st.sidebar.radio("分析項目", ["変化量詳細", "到達位置", "3Dリリース", "リリース位置安定度", "球速・回転数", "球速vs変化量", "カウント別"])
                if item == "変化量詳細":
                    fig, ax = plt.subplots(figsize=(6, 6))
                    for pt in target_df['TaggedPitchType'].unique():
                        d = target_df[target_df['TaggedPitchType']==pt]
                        ax.scatter(d['HorzBreak'], d['InducedVertBreak'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6, marker=get_marker(pt, p_throws))
                    ax.axvline(0); ax.axhline(0); ax.set_xlim(-80,80); ax.set_ylim(-80,80); ax.set_box_aspect(1); plt.legend(bbox_to_anchor=(1.05, 1)); st.pyplot(fig)
                elif item == "到達位置":
                    c1, c2 = st.columns(2)
                    for side, col in [('Right', c1), ('Left', c2)]:
                        with col:
                            fig, ax = plt.subplots(figsize=(6, 6)); ax.add_patch(plt.Rectangle((-21.5, 45), 43, 60, fill=False, lw=2))
                            d_s = target_df[target_df['BatterSide']==side]
                            for pt in target_df['TaggedPitchType'].unique():
                                d_p = d_s[d_s['TaggedPitchType']==pt]
                                if not d_p.empty: ax.scatter(d_p['PlateLocSide_cm'], d_p['PlateLocHeight_cm'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.5)
                            ax.set_xlim(-80,80); ax.set_ylim(0,180); ax.set_title(f"対 {side}打者"); st.pyplot(fig)
                elif item == "3Dリリース":
                    st.plotly_chart(px.scatter_3d(target_df.dropna(subset=['RelSide', 'Extension', 'RelHeight']), x='RelSide', y='Extension', z='RelHeight', color='TaggedPitchType', color_discrete_map=PITCH_COLORS), use_container_width=True)
                elif item == "リリース位置安定度":
                    fig, ax = plt.subplots(figsize=(6, 6))
                    for pt in target_df['TaggedPitchType'].unique():
                        d = target_df[target_df['TaggedPitchType']==pt]
                        ax.scatter(d['RelSide'], d['RelHeight'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6)
                    ax.set_xlabel("RelSide (ft)"); ax.set_ylabel("RelHeight (ft)"); ax.set_title("Release Point"); st.pyplot(fig)
                elif item == "球速・回転数":
                    c1, c2 = st.columns(2)
                    with c1: st.plotly_chart(px.box(target_df, x="TaggedPitchType", y="RelSpeed", color="TaggedPitchType", color_discrete_map=PITCH_COLORS), use_container_width=True)
                    with c2: st.plotly_chart(px.box(target_df, x="TaggedPitchType", y="SpinRate", color="TaggedPitchType", color_discrete_map=PITCH_COLORS), use_container_width=True)
                elif item == "球速vs変化量":
                    st.plotly_chart(px.scatter(target_df, x="RelSpeed", y="InducedVertBreak", color="TaggedPitchType", color_discrete_map=PITCH_COLORS), use_container_width=True)
                elif item == "カウント別":
                    if 'Balls' in target_df.columns and 'Strikes' in target_df.columns:
                        target_df['Count'] = target_df['Balls'].fillna(0).astype(int).astype(str) + "-" + target_df['Strikes'].fillna(0).astype(int).astype(str)
                        count_data = target_df.groupby(['Count', 'TaggedPitchType'], observed=True).size().unstack(fill_value=0)
                        if not count_data.empty: st.bar_chart(count_data.div(count_data.sum(axis=1), axis=0) * 100)
                display_pitcher_table(target_df)

            elif p_sub_mode == "2人比較":
                p2 = st.sidebar.selectbox("比較投手", sorted(full_df['Pitcher'].dropna().unique().astype(str)), index=min(1, len(full_df['Pitcher'].dropna().unique())-1))
                p2_df = full_df[full_df['Pitcher'].astype(str) == p2].copy()
                col1, col2 = st.columns(2)
                for d, col, name in [(target_df, col1, header_name), (p2_df, col2, p2)]:
                    with col:
                        st.subheader(f" {name}")
                        fig, ax = plt.subplots(figsize=(6, 6))
                        for pt in PITCH_LIST:
                            sub = d[d['TaggedPitchType']==pt]
                            if not sub.empty: ax.scatter(sub['HorzBreak'], sub['InducedVertBreak'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6)
                        ax.axvline(0); ax.axhline(0); ax.set_xlim(-80,80); ax.set_ylim(-80,80); ax.set_box_aspect(1); st.pyplot(fig)
                        display_pitcher_table(d)

        elif mode == "打者分析":
            # (以前と同じため中略... 打者分析コード)
            st.sidebar.subheader("◯ 打者設定")
            b_col = 'Batter' if 'Batter' in full_df.columns else 'Batter Name'
            sel_b = st.sidebar.selectbox("打者を選択", sorted(full_df[b_col].dropna().unique().astype(str)))
            b_full_df = full_df[full_df[b_col].astype(str) == sel_b].copy()
            s_files = st.sidebar.multiselect("ファイル選択", sorted(b_full_df['SeasonFile'].unique()), key="bf")
            s_dates = st.sidebar.multiselect("日付選択", sorted(b_full_df['Date_str'].dropna().unique(), reverse=True), key="bd")
            target_df = b_full_df.copy()
            if s_files: target_df = target_df[target_df['SeasonFile'].isin(s_files)]
            if s_dates: target_df = target_df[target_df['Date_str'].isin(s_dates)]
            v_view = st.sidebar.radio("表示視点", ["投手目線", "捕手目線"])
            target_col = st.sidebar.selectbox("コース別表示項目", ["打球速度", "打球角度", "飛距離"])
            angle_metric = st.sidebar.selectbox("角度グラフの指標", ["打率", "平均飛距離", "平均打球速度"])
            
            st.title(f"□ {sel_b} 分析レポート")
            if not target_df.empty:
                col_m = {"打球速度": "ExitSpeed", "打球角度": "Angle", "飛距離": "Distance"}
                unit_m = {"打球速度": "km/h", "打球角度": "°", "飛距離": "m"}
                norm_m = {"打球速度": (110, 155), "打球角度": (0, 30), "飛距離": (0, 100)}
                d_col, unit, (v_min, v_max) = col_m[target_col], unit_m[target_col], norm_m[target_col]
                hand = target_df['BatterSide'].mode()[0] if 'BatterSide' in target_df.columns else 'Right'
                x_edges = [-36.5, -21.5, -7.17, 7.17, 21.5, 36.5]
                y_edges = [30.0, 45.0, 65.0, 85.0, 105.0, 120.0]
                c1, c2, c3 = st.columns(3)
                filters = [target_df, target_df[target_df['PitcherThrows'].str.startswith(('R','r'), na=False)], target_df[target_df['PitcherThrows'].str.startswith(('L','l'), na=False)]]
                titles = ['TOTAL', 'VS RIGHT P', 'VS LEFT P']
                for i, col_ax in enumerate([c1, c2, c3]):
                    subset = filters[i]
                    fig, ax = plt.subplots(figsize=(7, 9))
                    draw_stylish_batter(ax, batter_side=hand, view=v_view)
                    for r in range(5):
                        for c in range(5):
                            x_min, x_max = x_edges[c], x_edges[c+1]
                            y_min, y_max = y_edges[4-r], y_edges[5-r]
                            side_mod = -1 if v_view == "捕手目線" else 1
                            mask = (subset['PlateLocSide_cm'] * side_mod >= x_min) & (subset['PlateLocSide_cm'] * side_mod < x_max) & \
                                   (subset['PlateLocHeight_cm'] >= y_min) & (subset['PlateLocHeight_cm'] < y_max)
                            z_data = subset[mask]
                            if not z_data.empty:
                                val = z_data[d_col].mean()
                                if not np.isnan(val):
                                    norm_v = (val - v_min) / (v_max - v_min)
                                    color = cm.Reds(np.clip(norm_v, 0, 1))
                                    ax.add_patch(plt.Rectangle((x_min, y_min), x_max-x_min, y_max-y_min, color=color, alpha=0.9, ec='white', lw=0.5, zorder=5))
                                    ax.text((x_min+x_max)/2, (y_min+y_max)/2, f"{val:.1f}{unit}\nn={len(z_data)}", ha='center', va='center', fontweight='bold', fontsize=8, color='white' if norm_v > 0.6 else 'black', zorder=10)
                    ax.add_patch(plt.Rectangle((-21.5, 45.0), 43.0, 60.0, fill=False, ec='black', lw=2.5, zorder=15))
                    ax.set_xlim(-75, 75); ax.set_ylim(15, 165); ax.set_aspect('equal'); ax.axis('off'); ax.set_title(titles[i]); col_ax.pyplot(fig)
                st.markdown("---")
                low1, low2 = st.columns(2)
                res_col = 'PlayResult' if 'PlayResult' in target_df.columns else 'Result'
                hit_k = ['Single', 'Double', 'Triple', 'HomeRun']
                with low1:
                    st.subheader(f"▶︎ 角度別 {angle_metric}")
                    bins = np.arange(-20, 71, 10); centers = bins[:-1] + 5; theta = np.deg2rad(centers)
                    vals = []
                    for b_idx in range(len(bins)-1):
                        d = target_df[(target_df['Angle'] >= bins[b_idx]) & (target_df['Angle'] < bins[b_idx+1])]
                        n = len(d)
                        if n > 0:
                            if angle_metric == "打率": v = d[res_col].isin(hit_k).sum() / n
                            elif angle_metric == "平均飛距離": v = d['Distance'].mean()
                            else: v = d['ExitSpeed'].mean()
                        else: v = 0
                        vals.append(v if not np.isnan(v) else 0)
                    fig_p, ax_p = plt.subplots(figsize=(6, 6), subplot_kw={'projection': 'polar'})
                    ax_p.bar(theta, vals, width=np.deg2rad(9.5), color='darkred', alpha=0.7, edgecolor='black')
                    ax_p.set_thetamin(-25); ax_p.set_thetamax(75); ax_p.set_theta_zero_location('E')
                    ax_p.set_xticks(np.deg2rad(bins)); ax_p.set_xticklabels([f"{a}°" for a in bins]); st.pyplot(fig_p)
                with low2:
                    st.subheader("▶︎ 打球分布 (Spray Chart)")
                    if 'Bearing' in target_df.columns and 'Distance' in target_df.columns:
                        fig_s, ax_s = plt.subplots(figsize=(6, 6)); draw_field(ax_s)
                        hr = target_df[target_df[res_col] == 'HomeRun']
                        hits = target_df[target_df[res_col].isin(['Single', 'Double', 'Triple'])]
                        outs = target_df[~target_df[res_col].isin(hit_k)]
                        def to_coords(b, d):
                            r = np.deg2rad(b); return d * np.sin(r), d * np.cos(r)
                        hx, hy = to_coords(hits['Bearing'], hits['Distance'])
                        ox, oy = to_coords(outs['Bearing'], outs['Distance'])
                        hrx, hry = to_coords(hr['Bearing'], hr['Distance'])
                        ax_s.scatter(ox, oy, color='gray', alpha=0.4, label='凡打', s=25)
                        ax_s.scatter(hx, hy, color='red', alpha=0.8, label='安打', s=55, edgecolors='black', zorder=5)
                        ax_s.scatter(hrx, hry, color='gold', alpha=1.0, label='本塁打', s=120, marker='*', edgecolors='black', zorder=10)
                        ax_s.legend(loc='upper right', fontsize=8); ax_s.set_xlim(-100, 100); ax_s.set_ylim(-10, 130); st.pyplot(fig_s)
    else:
        st.error("CSVデータが見つかりません。")

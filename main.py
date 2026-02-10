import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import japanize_matplotlib
import os
import plotly.express as px
import numpy as np

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

    # --- 2. 描画用共通関数 ---
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

    def draw_stylish_batter(ax, batter_side='Right', view_mode="投手目線"):
        if view_mode == "投手目線":
            x_offset = 50 if batter_side == 'Right' else -50
            flip = -1 if batter_side == 'Right' else 1
        else:
            x_offset = -50 if batter_side == 'Right' else 50
            flip = 1 if batter_side == 'Right' else -1
        color, alpha = '#333333', 0.12
        ax.add_patch(plt.Circle((x_offset, 130), 5, color=color, alpha=alpha, zorder=0))
        ax.add_patch(plt.Polygon(np.array([[x_offset-8, 80], [x_offset+8, 80], [x_offset+12, 125], [x_offset-12, 125]]), color=color, alpha=alpha, zorder=0))
        ax.add_patch(plt.Polygon(np.array([[x_offset-8, 80], [x_offset-4, 80], [x_offset-12, 20], [x_offset-20, 20]]), color=color, alpha=alpha, zorder=0))
        ax.add_patch(plt.Polygon(np.array([[x_offset+4, 80], [x_offset+8, 80], [x_offset+15, 20], [x_offset+8, 20]]), color=color, alpha=alpha, zorder=0))
        ax.add_patch(plt.Polygon(np.array([[x_offset+(10*flip), 115], [x_offset+(40*flip), 155], [x_offset+(43*flip), 152], [x_offset+(13*flip), 112]]), color=color, alpha=0.18, zorder=0))

    def display_full_pro_table(df):
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
        res['投球割合'] = res['Pitcher'].apply(lambda x: f"{x/total*100:.1f}% ({x}球)")
        res['TaggedPitchType'] = pd.Categorical(res['TaggedPitchType'], categories=PITCH_LIST, ordered=True)
        res = res.sort_values('TaggedPitchType').dropna(subset=['TaggedPitchType'])
        st.dataframe(res.rename(columns={'TaggedPitchType':'球種','RelSpeed':'平均(km/h)','SpinRate':'回転数','InducedVertBreak':'縦変化','HorzBreak':'横変化'}).style.format(precision=1), use_container_width=True, hide_index=True)

    # --- 3. データ読み込み ---
    @st.cache_data
    def load_data():
        DATA_DIR = "data"
        all_data = []
        if os.path.exists(DATA_DIR):
            for f in [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]:
                try:
                    temp = pd.read_csv(os.path.join(DATA_DIR, f))
                    cols = ['RelSpeed', 'InducedVertBreak', 'HorzBreak', 'RelHeight', 'RelSide', 'Extension', 'PlateLocSide', 'PlateLocHeight', 'ExitSpeed', 'Balls', 'Strikes']
                    for c in cols:
                        if c in temp.columns: temp[c] = pd.to_numeric(temp[c], errors='coerce')
                    for c in ['RelHeight', 'RelSide', 'Extension', 'PlateLocSide', 'PlateLocHeight']:
                        if c in temp.columns: temp[c] = temp[c] * 100
                    temp['SeasonFile'] = f
                    all_data.append(temp)
                except: pass
        return pd.concat(all_data, ignore_index=True) if all_data else None

    df_full = load_data()

    if df_full is not None:
        df_full['TaggedPitchType'] = df_full['TaggedPitchType'].replace('FourSeamFastBall', 'Fastball').fillna('Unknown').astype(str)
        df_full['Date_str'] = pd.to_datetime(df_full['Date'], errors='coerce').dt.strftime('%Y-%m-%d')
        
        # --- 4. タブ選択（session_stateによる同期） ---
        selected_mode = st.radio("🏠 分析モード選択", ["投手分析", "打撃分析"], horizontal=True, label_visibility="collapsed")

        # --- 5. サイドバーとメイン画面の動的制御 ---
        if selected_mode == "投手分析":
            # --- 投手サイドバー ---
            st.sidebar.title("🔥 PITCHER MENU")
            p_col = 'Pitcher' if 'Pitcher' in df_full.columns else 'Pitcher Name'
            p_list = sorted([str(p) for p in df_full[p_col].unique() if pd.notna(p)])
            sel_p = st.sidebar.selectbox("投手を選択", p_list)
            p_mode = st.sidebar.radio("レポート形式", ["総合レポート", "1人集中分析"])
            
            p_full = df_full[df_full[p_col].astype(str) == sel_p].copy()
            s_files = st.sidebar.multiselect("ファイル絞り込み", sorted(p_full['SeasonFile'].unique()))
            s_dates = st.sidebar.multiselect("日付絞り込み", sorted(p_full['Date_str'].dropna().unique(), reverse=True))
            
            target_df = p_full.copy()
            if s_files: target_df = target_df[target_df['SeasonFile'].isin(s_files)]
            if s_dates: target_df = target_df[target_df['Date_str'].isin(s_dates)]
            p_throws = target_df['PitcherThrows'].iloc[0] if not target_df.empty and 'PitcherThrows' in target_df.columns else 'Right'

            # --- 投手メイン画面 ---
            st.header(f"📊 {sel_p} 投手：分析結果")
            if p_mode == "総合レポート":
                c1, c2 = st.columns(2)
                with c1:
                    fig, ax = plt.subplots(figsize=(6, 6))
                    for pt in PITCH_LIST:
                        d = target_df[target_df['TaggedPitchType']==pt]
                        if not d.empty: ax.scatter(d['HorzBreak'], d['InducedVertBreak'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6, marker=get_marker(pt, p_throws))
                    ax.axvline(0, color='black', lw=1); ax.axhline(0, color='black', lw=1); ax.set_xlim(-80,80); ax.set_ylim(-80,80); ax.set_title("変化量(cm)"); st.pyplot(fig)
                with c2:
                    fig, ax = plt.subplots(figsize=(6, 6))
                    for pt in PITCH_LIST:
                        d = target_df[target_df['TaggedPitchType']==pt]
                        if not d.empty: ax.scatter(d['HorzRelAngle'], d['VertRelAngle'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6, marker=get_marker(pt, p_throws))
                    ax.axvline(0, color='black', lw=1); ax.axhline(0, color='black', lw=1); ax.set_xlim(-6,6); ax.set_ylim(-6,6); ax.set_title("リリース角"); st.pyplot(fig)
                display_full_pro_table(target_df)
            else:
                p_item = st.sidebar.radio("詳細項目", ["変化量詳細", "到達位置", "3Dリリース"])
                if p_item == "変化量詳細":
                    fig, ax = plt.subplots(figsize=(6,6))
                    for pt in target_df['TaggedPitchType'].unique():
                        d = target_df[target_df['TaggedPitchType']==pt]
                        ax.scatter(d['HorzBreak'], d['InducedVertBreak'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6)
                    ax.set_xlim(-80,80); ax.set_ylim(-80,80); ax.axvline(0); ax.axhline(0); ax.legend(bbox_to_anchor=(1.05, 1)); st.pyplot(fig)
                elif p_item == "到達位置":
                    c1, c2 = st.columns(2)
                    for side, col in [('Right', c1), ('Left', c2)]:
                        with col:
                            fig, ax = plt.subplots(figsize=(6, 6)); ax.add_patch(plt.Rectangle((-21.5, 45), 43, 60, fill=False, lw=2))
                            d_s = target_df[target_df['BatterSide']==side]
                            for pt in target_df['TaggedPitchType'].unique():
                                d_p = d_s[d_s['TaggedPitchType']==pt]
                                if not d_p.empty: ax.scatter(d_p['PlateLocSide'], d_p['PlateLocHeight'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6)
                            ax.set_xlim(-100,100); ax.set_ylim(0,200); ax.set_title(f"対 {side}打者"); st.pyplot(fig)
                elif p_item == "3Dリリース":
                    st.plotly_chart(px.scatter_3d(target_df.dropna(subset=['RelSide', 'Extension', 'RelHeight']), x='RelSide', y='Extension', z='RelHeight', color='TaggedPitchType', color_discrete_map=PITCH_COLORS), use_container_width=True)

        elif selected_mode == "打撃分析":
            # --- 打者サイドバー ---
            st.sidebar.title("⚾ BATTER MENU")
            b_col = 'Batter Name' if 'Batter Name' in df_full.columns else 'Batter'
            b_list = sorted([str(b) for b in df_full[b_col].unique() if pd.notna(b)])
            sel_b = st.sidebar.selectbox("打者を選択", b_list)
            view_mode = st.sidebar.radio("表示視点", ["投手目線", "捕手目線"])
            
            b_full = df_full[df_full[b_col] == sel_b].copy()
            
            # --- 打者メイン画面 ---
            st.header(f"🎯 {sel_b} 打者：打球速度ヒートマップ")
            if not b_full.empty:
                b_full['PlateLocSide_Plot'] = b_full['PlateLocSide'] * (-1 if view_mode == "捕手目線" else 1)
                b_hand = b_full['BatterSide'].mode()[0] if not b_full['BatterSide'].dropna().empty else 'Right'
                
                x_edges = [-36.5, -21.5, -7.17, 7.17, 21.5, 36.5]
                y_edges = [30.0, 45.0, 65.0, 85.0, 105.0, 120.0]
                V_MIN, V_MAX = 110, 155

                fig_h, axes_h = plt.subplots(1, 3, figsize=(20, 8), facecolor='white')
                filters_h = [b_full, b_full[b_full['PitcherThrows'] == 'Right'], b_full[b_full['PitcherThrows'] == 'Left']]
                titles_h = ['TOTAL', 'VS RIGHT P', 'VS LEFT P']

                for i, ax in enumerate(axes_h):
                    subset_h = filters_h[i]
                    draw_stylish_batter(ax, b_hand, view_mode)
                    for r in range(5):
                        for c in range(5):
                            x_min, x_max = x_edges[c], x_edges[c+1]
                            y_min, y_max = y_edges[4-r], y_edges[5-r]
                            zone_data = subset_h[(subset_h['PlateLocSide_Plot'] >= x_min) & (subset_h['PlateLocSide_Plot'] < x_max) &
                                                (subset_h['PlateLocHeight'] >= y_min) & (subset_h['PlateLocHeight'] < y_max)]
                            if not zone_data.empty:
                                avg_v = zone_data['ExitSpeed'].mean()
                                if pd.notna(avg_v):
                                    norm = (avg_v - V_MIN) / (V_MAX - V_MIN)
                                    color = plt.cm.Reds(np.clip(norm, 0, 1))
                                    ax.add_patch(plt.Rectangle((x_min, y_min), x_max-x_min, y_max-y_min, color=color, alpha=0.9, ec='white', lw=0.5))
                                    ax.text((x_min + x_max)/2, (y_min + y_max)/2, f"{avg_v:.1f}\n$n$={len(zone_data)}", ha='center', va='center', fontweight='bold', fontsize=8, color='white' if norm > 0.6 else 'black')
                    ax.add_patch(plt.Rectangle((-21.5, 45.0), 43.0, 60.0, fill=False, edgecolor='black', lw=2))
                    ax.set_xlim(-80, 80); ax.set_ylim(10, 160); ax.set_aspect('equal'); ax.axis('off'); ax.set_title(titles_h[i])
                st.pyplot(fig_h)
            else:
                st.warning("この打者のデータがありません。")

    else:
        st.error("dataフォルダにCSVが見つかりません。")

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import japanize_matplotlib
import os
import plotly.express as px

# --- パスワード保護 ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = None
    if st.session_state["password_correct"] == True: return True
    def password_entered():
        if st.session_state["password_input"] == "wbc1901":
            st.session_state["password_correct"] = True
        else:
            st.session_state["password_correct"] = False
    st.title("🔐 早稲田大学野球部 データ分析ツール Pro")
    st.text_input("パスワードを入力してください", type="password", on_change=password_entered, key="password_input")
    if st.session_state["password_correct"] == False:
        st.error("😕 パスワードが違います。")
    return False

if check_password():
    st.set_page_config(layout="wide", page_title="野球部データ分析ツール Pro")

    # --- 基本設定 ---
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

    # --- 集計表関数 ---
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
        
        # 指標の計算
        whiff_res = df.groupby('TaggedPitchType', observed=True).apply(lambda x: (x['is_whiff'].sum() / x['is_swing'].sum() * 100) if x['is_swing'].sum() > 0 else 0).reset_index(name='Whiff%')
        strike_res = df.groupby('TaggedPitchType', observed=True).apply(lambda x: x['is_strike'].mean() * 100).reset_index(name='Strike%')
        
        res = res.merge(whiff_res, on='TaggedPitchType').merge(strike_res, on='TaggedPitchType')
        res['投球割合(球数)'] = res['Pitcher'].apply(lambda x: f"{x/total*100:.1f}% ({x})")
        
        res['TaggedPitchType'] = pd.Categorical(res['TaggedPitchType'], categories=PITCH_LIST, ordered=True)
        res = res.sort_values('TaggedPitchType').dropna(subset=['TaggedPitchType'])
        st.dataframe(res.rename(columns={'TaggedPitchType':'球種','RelSpeed':'平均(km/h)','SpinRate':'回転数','InducedVertBreak':'縦変化','HorzBreak':'横変化'}).style.format(precision=1), use_container_width=True, hide_index=True)

    # --- データ読み込み ---
    DATA_DIR = "data"
    all_data = []
    if os.path.exists(DATA_DIR):
        for f in [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]:
            try:
                temp = pd.read_csv(os.path.join(DATA_DIR, f))
                num_cols = ['RelSpeed', 'InducedVertBreak', 'HorzBreak', 'RelHeight', 'RelSide', 'Extension', 'VertRelAngle', 'HorzRelAngle', 'SpinRate', 'PlateLocSide', 'PlateLocHeight']
                for c in num_cols:
                    if c in temp.columns: temp[c] = pd.to_numeric(temp[c], errors='coerce')
                # フィートからセンチメートルへの変換（必要な場合）
                for c in ['RelHeight', 'RelSide', 'Extension', 'PlateLocSide', 'PlateLocHeight']:
                    if c in temp.columns: temp[c] = temp[c] * 100
                temp['SeasonFile'] = f
                all_data.append(temp)
            except: pass

    if all_data:
        full_df = pd.concat(all_data, ignore_index=True)
        full_df['TaggedPitchType'] = full_df['TaggedPitchType'].replace('FourSeamFastBall', 'Fastball').fillna('Unknown').astype(str)
        full_df['Date_str'] = pd.to_datetime(full_df['Date'], errors='coerce').dt.strftime('%Y-%m-%d')

        st.sidebar.title("📊 MENU")
        mode = st.sidebar.radio("モード選択", ["総合レポート", "1人集中分析", "2人比較"])
        p1 = st.sidebar.selectbox("投手を選択", sorted(full_df['Pitcher'].unique().astype(str)))
        
        p1_full = full_df[full_df['Pitcher'].astype(str) == p1].copy()
        s_files = st.sidebar.multiselect("ファイル選択", sorted(p1_full['SeasonFile'].unique()), key="f1")
        s_dates = st.sidebar.multiselect("日付選択", sorted(p1_full['Date_str'].dropna().unique(), reverse=True), key="d1")
        target_df1 = p1_full.copy()
        if s_files: target_df1 = target_df1[target_df1['SeasonFile'].isin(s_files)]
        if s_dates: target_df1 = target_df1[target_df1['Date_str'].isin(s_dates)]
        p1_throws = target_df1['PitcherThrows'].iloc[0] if not target_df1.empty else 'Right'

        if mode == "総合レポート":
            st.header(f"📋 {p1} 投手：総合レポート")
            c1, c2 = st.columns(2)
            with c1:
                fig, ax = plt.subplots(figsize=(6, 6)) # サイズを正方形に固定
                for pt in PITCH_LIST:
                    d = target_df1[target_df1['TaggedPitchType']==pt]
                    if not d.empty: ax.scatter(d['HorzBreak'], d['InducedVertBreak'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6, marker=get_marker(pt, p1_throws))
                ax.axvline(0, color='black', lw=1); ax.axhline(0, color='black', lw=1); ax.set_xlim(-80,80); ax.set_ylim(-80,80)
                ax.set_title("変化量(cm)"); ax.set_box_aspect(1); st.pyplot(fig)
            with c2:
                fig, ax = plt.subplots(figsize=(6, 6))
                for pt in PITCH_LIST:
                    d = target_df1[target_df1['TaggedPitchType']==pt]
                    if not d.empty: ax.scatter(d['HorzRelAngle'], d['VertRelAngle'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6, marker=get_marker(pt, p1_throws))
                ax.axvline(0, color='black', lw=1); ax.axhline(0, color='black', lw=1); ax.set_xlim(-6,6); ax.set_ylim(-6,6)
                ax.set_title("リリースアングル"); ax.set_box_aspect(1); st.pyplot(fig)
            display_full_pro_table(target_df1)

        elif mode == "1人集中分析":
            item = st.sidebar.radio("分析項目", ["変化量詳細", "到達位置", "3Dリリースポイント", "リリース位置の安定度", "球速・回転数の分布", "球速 vs 変化量相関", "カウント別傾向"])
            st.header(f"👤 {p1}：{item}")
            
            if item == "変化量詳細":
                fig, ax = plt.subplots(figsize=(6, 6))
                for pt in target_df1['TaggedPitchType'].unique():
                    d = target_df1[target_df1['TaggedPitchType']==pt]
                    ax.scatter(d['HorzBreak'], d['InducedVertBreak'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6, marker=get_marker(pt, p1_throws))
                ax.axvline(0); ax.axhline(0); ax.set_xlim(-80,80); ax.set_ylim(-80,80); ax.set_box_aspect(1); plt.legend(bbox_to_anchor=(1.05, 1)); st.pyplot(fig)
            elif item == "到達位置":
                c1, c2 = st.columns(2)
                for side, col in [('Right', c1), ('Left', c2)]:
                    with col:
                        fig, ax = plt.subplots(figsize=(6, 6)); ax.add_patch(plt.Rectangle((-25, 45), 50, 60, fill=False, lw=2))
                        d_s = target_df1[target_df1['BatterSide']==side]
                        for pt in target_df1['TaggedPitchType'].unique():
                            d_p = d_s[d_s['TaggedPitchType']==pt]
                            if not d_p.empty: ax.scatter(d_p['PlateLocSide'], d_p['PlateLocHeight'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6)
                        ax.set_xlim(-100,100); ax.set_ylim(0,200); ax.set_box_aspect(1); ax.set_title(f"対 {side}打者"); st.pyplot(fig)
            elif item == "3Dリリースポイント":
                plot_df = target_df1.dropna(subset=['RelSide', 'Extension', 'RelHeight'])
                st.plotly_chart(px.scatter_3d(plot_df, x='RelSide', y='Extension', z='RelHeight', color='TaggedPitchType', color_discrete_map=PITCH_COLORS), use_container_width=True)
            elif item == "リリース位置の安定度":
                fig, ax = plt.subplots(figsize=(6, 6))
                for pt in target_df1['TaggedPitchType'].unique():
                    d = target_df1[target_df1['TaggedPitchType']==pt]
                    ax.scatter(d['RelSide'], d['RelHeight'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6)
                ax.set_xlim(-150,150); ax.set_ylim(0,250); ax.set_box_aspect(1); st.pyplot(fig)
            elif item == "球速・回転数の分布":
                c1, c2 = st.columns(2)
                with c1: st.plotly_chart(px.box(target_df1, x="TaggedPitchType", y="RelSpeed", color="TaggedPitchType", color_discrete_map=PITCH_COLORS), use_container_width=True)
                with c2: st.plotly_chart(px.box(target_df1, x="TaggedPitchType", y="SpinRate", color="TaggedPitchType", color_discrete_map=PITCH_COLORS), use_container_width=True)
            elif item == "球速 vs 変化量相関":
                st.plotly_chart(px.scatter(target_df1, x="RelSpeed", y="InducedVertBreak", color="TaggedPitchType", color_discrete_map=PITCH_COLORS), use_container_width=True)
            elif item == "カウント別傾向":
                target_df1['Count'] = target_df1['Balls'].fillna(0).astype(int).astype(str) + "-" + target_df1['Strikes'].fillna(0).astype(int).astype(str)
                count_data = target_df1.groupby(['Count', 'TaggedPitchType'], observed=True).size().unstack(fill_value=0)
                st.bar_chart(count_data.div(count_data.sum(axis=1), axis=0) * 100)
            
            display_full_pro_table(target_df1)

        elif mode == "2人比較":
            st.sidebar.markdown("---")
            p2 = st.sidebar.selectbox("比較対象(投手2)を選択", sorted(full_df['Pitcher'].unique().astype(str)), index=min(1, len(full_df['Pitcher'].unique())-1))
            p2_full = full_df[full_df['Pitcher'].astype(str) == p2].copy()
            comp_item = st.sidebar.radio("比較項目", ["変化量", "リリース位置", "球速分布"])
            
            st.header(f"⚖️ {p1} vs {p2}")
            col1, col2 = st.columns(2)
            
            for d, col, name in [(target_df1, col1, p1), (p2_full, col2, p2)]:
                with col:
                    st.subheader(f"👤 {name}")
                    if comp_item == "変化量":
                        fig, ax = plt.subplots(figsize=(6, 6))
                        for pt in PITCH_LIST:
                            sub = d[d['TaggedPitchType']==pt]
                            if not sub.empty: ax.scatter(sub['HorzBreak'], sub['InducedVertBreak'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6)
                        ax.axvline(0); ax.axhline(0); ax.set_xlim(-80,80); ax.set_ylim(-80,80); ax.set_box_aspect(1); st.pyplot(fig)
                    elif comp_item == "リリース位置":
                        fig, ax = plt.subplots(figsize=(6, 6))
                        for pt in PITCH_LIST:
                            sub = d[d['TaggedPitchType']==pt]
                            if not sub.empty: ax.scatter(sub['RelSide'], sub['RelHeight'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6)
                        ax.set_xlim(-150,150); ax.set_ylim(0,250); ax.set_box_aspect(1); st.pyplot(fig)
                    elif comp_item == "球速分布":
                        st.plotly_chart(px.box(d, x='TaggedPitchType', y='RelSpeed', color='TaggedPitchType', color_discrete_map=PITCH_COLORS), use_container_width=True)
                    display_full_pro_table(d)

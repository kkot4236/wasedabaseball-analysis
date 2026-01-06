import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import japanize_matplotlib
import os
import plotly.express as px

# ==================================================
# 0. パスワード保護
# ==================================================
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = None
    if st.session_state["password_correct"] == True: return True
    def password_entered():
        if st.session_state["password_input"] == "waseda123":
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
        if pitch_type == 'TwoSeamFastBall': return 'p'
        return 'o'

    # --- 集計表 ---
    def display_full_pro_table(df):
        if df.empty: return
        total = len(df)
        df = df.copy()
        df['is_strike'] = df['PitchCall'].isin(['StrikeCalled', 'StrikeSwinging', 'FoulBall', 'InPlayOut', 'Single', 'Double', 'Triple', 'HomeRun'])
        df['is_whiff'] = df['PitchCall'] == 'StrikeSwinging'
        df['is_swing'] = df['PitchCall'].isin(['StrikeSwinging', 'FoulBall', 'InPlayOut', 'Single', 'Double', 'Triple', 'HomeRun'])
        res = df.groupby('TaggedPitchType', observed=True).agg(
            count=('Pitcher', 'count'), 平均球速=('RelSpeed', 'mean'), 最高球速=('RelSpeed', 'max'),
            回転数=('SpinRate', 'mean'), 縦変化=('InducedVertBreak', 'mean'), 横変化=('HorzBreak', 'mean'),
            アングル縦=('VertRelAngle', 'mean'), アングル横=('HorzRelAngle', 'mean'),
            空振り率=('is_whiff', lambda x: (x.sum() / df.loc[x.index, 'is_swing'].sum() * 100) if df.loc[x.index, 'is_swing'].sum() > 0 else 0),
            ストライク率=('is_strike', lambda x: x.mean() * 100)
        ).reset_index()
        res['投球割合(球数)'] = res['count'].apply(lambda x: f"{x/total*100:.1f}% ({x})")
        res['TaggedPitchType'] = pd.Categorical(res['TaggedPitchType'], categories=PITCH_LIST, ordered=True)
        res = res.sort_values('TaggedPitchType').dropna(subset=['TaggedPitchType'])
        res = res[['TaggedPitchType', '投球割合(球数)', '平均球速', '最高球速', '回転数', '縦変化', '横変化', 'アングル縦', 'アングル横', '空振り率', 'ストライク率']]
        res = res.rename(columns={'TaggedPitchType': '球種', '平均球速': '平均(km/h)', '最高球速': '最高(km/h)', '縦変化': '縦変化(cm)', '横変化': '横変化(cm)', '空振り率': 'Whiff%', 'ストライク率': 'Strike%'})
        st.dataframe(res.style.format(precision=1, subset=['平均(km/h)', '最高(km/h)', '回転数', '縦変化(cm)', '横変化(cm)', 'アングル縦', 'アングル横', 'Whiff%', 'Strike%']), use_container_width=True, hide_index=True)

    # --- データ読み込み ---
    DATA_DIR = "data"
    all_data = []
    if os.path.exists(DATA_DIR):
        for f in [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]:
            try:
                temp = pd.read_csv(os.path.join(DATA_DIR, f))
                for c in ['PlateLocSide', 'PlateLocHeight', 'RelPosSide', 'RelPosHeight', 'Extension', 'RelSpeed', 'InducedVertBreak', 'HorzBreak', 'SpinRate', 'VertRelAngle', 'HorzRelAngle']:
                    if c in temp.columns: temp[c] = pd.to_numeric(temp[c], errors='coerce')
                # 単位変換
                for c in ['PlateLocSide', 'PlateLocHeight', 'RelPosSide', 'RelPosHeight', 'Extension']:
                    if c in temp.columns: temp[c] = temp[c] * 100
                temp['SeasonFile'] = f
                all_data.append(temp)
            except: pass

    if all_data:
        full_df = pd.concat(all_data, ignore_index=True)
        # 球種名の徹底クレンジング
        full_df['TaggedPitchType'] = full_df['TaggedPitchType'].replace('FourSeamFastBall', 'Fastball').fillna('Unknown').astype(str).str.strip()
        full_df['Date_str'] = pd.to_datetime(full_df['Date'], errors='coerce').dt.strftime('%Y-%m-%d')

        st.sidebar.title("📊 MENU")
        mode = st.sidebar.radio("モード選択", ["総合レポート", "1人集中分析", "2人比較"])
        p1 = st.sidebar.selectbox("投手を選択", sorted(full_df['Pitcher'].unique().astype(str)))
        p1_df = full_df[full_df['Pitcher'].astype(str) == p1].copy()
        p1_throws = p1_df['PitcherThrows'].iloc[0] if 'PitcherThrows' in p1_df.columns else 'Right'

        s_dates = st.sidebar.multiselect("日付選択", sorted(p1_df['Date_str'].dropna().unique(), reverse=True))
        target_df1 = p1_df.copy()
        if s_dates: target_df1 = target_df1[target_df1['Date_str'].isin(s_dates)]

        if mode == "総合レポート":
            st.header(f"📋 {p1} 投手：総合レポート")
            c1, c2 = st.columns(2)
            with c1:
                fig, ax = plt.subplots(figsize=(6, 5))
                for pt in PITCH_LIST:
                    d = target_df1[target_df1['TaggedPitchType'] == pt]
                    if not d.empty: ax.scatter(d['HorzBreak'], d['InducedVertBreak'], color=PITCH_COLORS.get(pt, '#808080'), marker=get_marker(pt, p1_throws), label=pt, alpha=0.6)
                ax.axvline(0, color='black', lw=1); ax.axhline(0, color='black', lw=1); ax.set_xlim(-80, 80); ax.set_ylim(-80, 80); ax.set_box_aspect(1); ax.set_title("変化量 [cm]"); ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left'); st.pyplot(fig)
            with c2:
                fig, ax = plt.subplots(figsize=(6, 5))
                for pt in PITCH_LIST:
                    d = target_df1[target_df1['TaggedPitchType'] == pt]
                    if not d.empty: ax.scatter(d['HorzRelAngle'], d['VertRelAngle'], color=PITCH_COLORS.get(pt, '#808080'), marker=get_marker(pt, p1_throws), label=pt, alpha=0.6)
                ax.axvline(0, color='black', lw=1); ax.axhline(0, color='black', lw=1); ax.set_xlim(-6, 6); ax.set_ylim(-6, 6); ax.set_box_aspect(1); ax.set_title("リリースアングル [度]"); ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left'); st.pyplot(fig)
            display_full_pro_table(target_df1)

        elif mode == "1人集中分析":
            st.sidebar.markdown("---")
            available_pitches = sorted(target_df1['TaggedPitchType'].unique())
            selected_pitches = st.sidebar.multiselect("表示する球種", available_pitches, default=available_pitches)
            filtered_df1 = target_df1[target_df1['TaggedPitchType'].isin(selected_pitches)].copy()
            item = st.sidebar.radio("分析項目", ["変化量詳細", "到達位置", "3Dリリースポイント", "リリース位置の安定度", "球速・回転数の分布", "球速 vs 変化量相関", "カウント別傾向"])
            
            if filtered_df1.empty:
                st.warning("表示するデータがありません。")
            else:
                if item == "3Dリリースポイント":
                    # 3Dに必要なデータが欠損している行を削除
                    plot_df = filtered_df1.dropna(subset=['RelPosSide', 'Extension', 'RelPosHeight'])
                    fig = px.scatter_3d(plot_df, x='RelPosSide', y='Extension', z='RelPosHeight', color='TaggedPitchType', color_discrete_map=PITCH_COLORS, opacity=0.7)
                    st.plotly_chart(fig, use_container_width=True)
                elif item == "球速・回転数の分布":
                    c1, c2 = st.columns(2)
                    with c1: st.plotly_chart(px.box(filtered_df1, x="TaggedPitchType", y="RelSpeed", color="TaggedPitchType", color_discrete_map=PITCH_COLORS, title="球速分布"), use_container_width=True)
                    with c2: st.plotly_chart(px.box(filtered_df1, x="TaggedPitchType", y="SpinRate", color="TaggedPitchType", color_discrete_map=PITCH_COLORS, title="回転数分布"), use_container_width=True)
                elif item == "球速 vs 変化量相関":
                    fig = px.scatter(filtered_df1, x="RelSpeed", y="InducedVertBreak", color="TaggedPitchType", color_discrete_map=PITCH_COLORS)
                    st.plotly_chart(fig, use_container_width=True)
                # (その他の項目はシンプルなmatplotlibなのでエラーが起きにくい)
                elif item == "変化量詳細":
                    fig, ax = plt.subplots(); 
                    for pt in selected_pitches:
                        d = filtered_df1[filtered_df1['TaggedPitchType']==pt]
                        if not d.empty: ax.scatter(d['HorzBreak'], d['InducedVertBreak'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6)
                    ax.axvline(0); ax.axhline(0); ax.set_xlim(-80,80); ax.set_ylim(-80,80); ax.set_box_aspect(1); st.pyplot(fig)
                elif item == "到達位置":
                    c1, c2 = st.columns(2)
                    for side, col in [('Right', c1), ('Left', c2)]:
                        with col:
                            fig, ax = plt.subplots(); ax.add_patch(plt.Rectangle((-25, 45), 50, 60, fill=False))
                            d_s = filtered_df1[filtered_df1['BatterSide']==side]
                            for pt in selected_pitches:
                                d_p = d_s[d_s['TaggedPitchType']==pt]
                                if not d_p.empty: ax.scatter(d_p['PlateLocSide'], d_p['PlateLocHeight'], color=PITCH_COLORS.get(pt,'gray'), alpha=0.6)
                            ax.set_xlim(-100,100); ax.set_ylim(0,200); ax.set_box_aspect(1); st.pyplot(fig)
                elif item == "リリース位置の安定度":
                    fig, ax = plt.subplots()
                    for pt in selected_pitches:
                        d = filtered_df1[filtered_df1['TaggedPitchType']==pt]
                        if not d.empty: ax.scatter(d['RelPosSide'], d['RelPosHeight'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6)
                    ax.set_box_aspect(1); st.pyplot(fig)
                elif item == "カウント別傾向":
                    filtered_df1['Count'] = filtered_df1['Balls'].astype(int).astype(str) + "-" + filtered_df1['Strikes'].astype(int).astype(str)
                    count_data = filtered_df1.groupby(['Count', 'TaggedPitchType'], observed=True).size().unstack(fill_value=0)
                    st.bar_chart(count_data.div(count_data.sum(axis=1), axis=0) * 100)

            st.subheader("📊 詳細スタッツ")
            display_full_pro_table(filtered_df1)
    else:
        st.warning("dataフォルダにCSVが見つかりません。")

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import japanize_matplotlib
import os

# ==================================================
# 0. パスワード保護機能
# ==================================================
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = None
    if st.session_state["password_correct"] == True:
        return True

    def password_entered():
        if st.session_state["password_input"] == "waseda123":
            st.session_state["password_correct"] = True
        else:
            st.session_state["password_correct"] = False

    st.title("🔐 早稲田大学野球部 データ分析ツール")
    st.text_input("パスワードを入力してください", type="password", on_change=password_entered, key="password_input")
    if st.session_state["password_correct"] == False:
        st.error("😕 パスワードが違います。")
    return False

if check_password():
    st.set_page_config(layout="wide", page_title="野球部データ分析ツール")

    # --- 基本設定 ---
    PITCH_LIST = ['Fastball', 'Slider', 'Cutter', 'Curveball', 'Splitter', 'ChangeUp', 'Sinker', 'TwoSeamFastBall']
    PITCH_COLORS = {
        'Fastball': '#FF4B4B', 'Slider': '#1E90FF', 'Cutter': '#FF1493', 
        'Curveball': '#32CD32', 'Splitter': '#40E0D0', 'ChangeUp': '#8A2BE2', 
        'Sinker': '#FFA500', 'TwoSeamFastBall': '#FF8C00'
    }

    # マーカー取得関数（左右と球種に基づいて決定）
    def get_marker(pitch_type, throws):
        if pitch_type == 'Fastball': return 'o'          # ●
        if pitch_type in ['Slider', 'Cutter']:
            return '<' if throws == 'Right' else '>'    # 右投げ◀, 左投げ▶
        if pitch_type == 'Splitter': return 's'         # ■
        if pitch_type in ['ChangeUp', 'Sinker']: return 'v' # ▼
        if pitch_type == 'Curveball': return '^'        # ▲
        if pitch_type == 'TwoSeamFastBall': return 'p'  # ⬠
        return 'o'

    # --- 共通：集計表作成関数（インデックス非表示版） ---
    def display_full_summary_table(df):
        if df.empty: return
        total_pitches = len(df)
        res = df.groupby('TaggedPitchType', observed=True).agg(
            count=('Pitcher', 'count'),
            平均球速=('RelSpeed', 'mean'),
            最高球速=('RelSpeed', 'max'),
            回転数=('SpinRate', 'mean'),
            縦変化=('InducedVertBreak', 'mean'),
            横変化=('HorzBreak', 'mean'),
            アングル縦=('VertRelAngle', 'mean'),
            アングル横=('HorzRelAngle', 'mean')
        ).reset_index()
        
        res['投球割合(球数)'] = res['count'].apply(lambda x: f"{x/total_pitches*100:.1f}% ({x})")
        res['TaggedPitchType'] = pd.Categorical(res['TaggedPitchType'], categories=PITCH_LIST, ordered=True)
        res = res.sort_values('TaggedPitchType').dropna(subset=['TaggedPitchType'])
        
        res = res[['TaggedPitchType', '投球割合(球数)', '平均球速', '最高球速', '回転数', '縦変化', '横変化', 'アングル縦', 'アングル横']]
        res = res.rename(columns={
            'TaggedPitchType': '球種',
            '平均球速': '平均(km/h)', '最高球速': '最高(km/h)',
            '縦変化': '縦変化(cm)', '横変化': '横変化(cm)',
            'アングル縦': 'リリースアングル(縦)', 'アングル横': 'リリースアングル(横)'
        })
        
        # hide_index=True で左側の数字を消す
        st.dataframe(
            res.style.format(precision=1, subset=['平均(km/h)', '最高(km/h)', '回転数', '縦変化(cm)', '横変化(cm)', 'リリースアングル(縦)', 'リリースアングル(横)']), 
            use_container_width=True,
            hide_index=True
        )

    # --- データ読み込み ---
    DATA_DIR = "data"
    all_data = []
    if os.path.exists(DATA_DIR):
        csv_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
        for filename in csv_files:
            filepath = os.path.join(DATA_DIR, filename)
            try:
                temp_df = pd.read_csv(filepath)
                for col in ['PlateLocSide', 'PlateLocHeight', 'RelPosSide', 'RelPosHeight']:
                    if col in temp_df.columns: temp_df[col] = temp_df[col] * 100
                temp_df['SeasonFile'] = filename
                all_data.append(temp_df)
            except: pass

    if all_data:
        full_df = pd.concat(all_data, ignore_index=True)
        full_df['TaggedPitchType'] = full_df['TaggedPitchType'].replace('FourSeamFastBall', 'Fastball')
        full_df['Date_str'] = pd.to_datetime(full_df['Date'], errors='coerce').dt.strftime('%Y-%m-%d')

        # --- サイドバー：メニュー ---
        st.sidebar.title("📊 MENU")
        mode = st.sidebar.radio("モード選択", ["総合レポート", "1人集中分析", "2人比較"])
        st.sidebar.markdown("---")
        
        p1 = st.sidebar.selectbox("投手Aを選択", sorted(full_df['Pitcher'].unique().astype(str)), key="p1_select")
        p1_df = full_df[full_df['Pitcher'].astype(str) == p1]
        p1_throws = p1_df['PitcherThrows'].iloc[0] if 'PitcherThrows' in p1_df.columns else 'Right'

        st.sidebar.subheader("📅 絞り込み")
        s_files = st.sidebar.multiselect("ファイル選択", sorted(p1_df['SeasonFile'].unique()))
        s_dates = st.sidebar.multiselect("日付選択", sorted(p1_df['Date_str'].dropna().unique(), reverse=True))
        
        target_df1 = p1_df.copy()
        if s_files: target_df1 = target_df1[target_df1['SeasonFile'].isin(s_files)]
        if s_dates: target_df1 = target_df1[target_df1['Date_str'].isin(s_dates)]

        # --- 共通グラフ関数（正方形・タイトル・凡例・マーカー） ---
        def get_fig(df, mode_name, title_text, throws):
            fig, ax = plt.subplots(figsize=(6, 5))
            for pt in PITCH_LIST:
                d = df[df['TaggedPitchType'] == pt]
                if d.empty: continue
                color = PITCH_COLORS.get(pt, '#808080')
                marker = get_marker(pt, throws)
                
                if mode_name == "変化量 (Break)":
                    ax.scatter(d['HorzBreak'], d['InducedVertBreak'], color=color, marker=marker, label=pt, alpha=0.6)
                    ax.set_xlim(-80, 80); ax.set_ylim(-80, 80)
                elif mode_name == "リリースアングル (Angle)":
                    ax.scatter(d['HorzRelAngle'], d['VertRelAngle'], color=color, marker=marker, label=pt, alpha=0.6)
                    ax.set_xlim(-6, 6); ax.set_ylim(-6, 6)
                elif mode_name == "リリース位置 (RelPos)":
                    ax.scatter(d['RelPosSide'], d['RelPosHeight'], color=color, marker=marker, label=pt, alpha=0.6)
                    ax.set_xlim(-150, 150); ax.set_ylim(0, 300)
            
            ax.axvline(0, color='black', lw=1); ax.axhline(0, color='black', lw=1)
            ax.set_box_aspect(1)
            ax.set_title(title_text, fontsize=12, fontweight='bold')
            ax.grid(True, alpha=0.3)
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0, fontsize=9)
            return fig

        # --- 各モードの表示 ---
        if mode == "総合レポート":
            st.header(f"📋 {p1} 投手：総合レポート")
            c1, c2 = st.columns(2)
            with c1: st.pyplot(get_fig(target_df1, "変化量 (Break)", "変化量 [cm]", p1_throws))
            with c2: st.pyplot(get_fig(target_df1, "リリースアングル (Angle)", "リリースアングル [度]", p1_throws))
            st.subheader("📊 総合集計スタッツ")
            display_full_summary_table(target_df1)

        elif mode == "1人集中分析":
            st.sidebar.subheader("👁 分析項目の選択")
            analysis_item = st.sidebar.radio("項目を選択", ["変化量 (Break)", "リリースアングル (Angle)", "到達位置 (PlateLoc)", "リリース位置 (RelPos)"])
            st.header(f"👤 {p1} 投手：{analysis_item}")

            if analysis_item == "到達位置 (PlateLoc)":
                c1, c2 = st.columns(2)
                for side, col, title in [('Right', c1, '到達位置: 対 右打者'), ('Left', c2, '到達位置: 対 左打者')]:
                    with col:
                        fig, ax = plt.subplots(figsize=(6, 5))
                        ax.add_patch(plt.Rectangle((-25, 45), 50, 60, fill=False, lw=2))
                        d_s = target_df1[target_df1['BatterSide'] == side]
                        for pt in PITCH_LIST:
                            d_p = d_s[d_s['TaggedPitchType'] == pt]
                            if not d_p.empty:
                                ax.scatter(d_p['PlateLocSide'], d_p['PlateLocHeight'], color=PITCH_COLORS[pt], marker=get_marker(pt, p1_throws), label=pt, alpha=0.6)
                        ax.set_xlim(-100, 100); ax.set_ylim(0, 200); ax.set_title(title, fontweight='bold'); ax.set_box_aspect(1)
                        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=9)
                        st.pyplot(fig)
            else:
                st.pyplot(get_fig(target_df1, analysis_item, analysis_item, p1_throws))
            
            st.subheader("📊 球種別スタッツ")
            display_full_summary_table(target_df1)

        elif mode == "2人比較":
            st.sidebar.markdown("---")
            p2 = st.sidebar.selectbox("投手Bを選択", sorted(full_df['Pitcher'].unique().astype(str)), key="p2_select")
            p2_df = full_df[full_df['Pitcher'].astype(str) == p2]
            p2_throws = p2_df['PitcherThrows'].iloc[0] if 'PitcherThrows' in p2_df.columns else 'Right'
            
            target_df2 = p2_df.copy()
            if s_files: target_df2 = target_df2[target_df2['SeasonFile'].isin(s_files)]
            if s_dates: target_df2 = target_df2[target_df2['Date_str'].isin(s_dates)]

            comp_item = st.sidebar.radio("比較項目を選択", ["変化量 (Break)", "リリースアングル (Angle)", "到達位置 (PlateLoc)"])
            st.header(f"⚖️ {p1} vs {p2}：{comp_item}")
            
            cl, cr = st.columns(2)
            if comp_item == "到達位置 (PlateLoc)":
                for df_t, col, name, thr in [(target_df1, cl, p1, p1_throws), (target_df2, cr, p2, p2_throws)]:
                    with col:
                        fig, ax = plt.subplots(figsize=(6, 5))
                        ax.add_patch(plt.Rectangle((-25, 45), 50, 60, fill=False, lw=2))
                        d_s = df_t[df_t['BatterSide'] == 'Right']
                        for pt in PITCH_LIST:
                            d_p = d_s[d_s['TaggedPitchType'] == pt]
                            if not d_p.empty:
                                ax.scatter(d_p['PlateLocSide'], d_p['PlateLocHeight'], color=PITCH_COLORS[pt], marker=get_marker(pt, thr), label=pt, alpha=0.6)
                        ax.set_xlim(-100, 100); ax.set_ylim(0, 200); ax.set_title(f"{name}: 対右", fontweight='bold'); ax.set_box_aspect(1)
                        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8); st.pyplot(fig)
            else:
                with cl: st.pyplot(get_fig(target_df1, comp_item, f"{p1}: {comp_item}", p1_throws))
                with cr: st.pyplot(get_fig(target_df2, comp_item, f"{p2}: {comp_item}", p2_throws))
            
            st.markdown("---")
            st.subheader(f"📊 {p1} のスタッツ"); display_full_summary_table(target_df1)
            st.subheader(f"📊 {p2} のスタッツ"); display_full_summary_table(target_df2)
    else:
        st.warning("dataフォルダにCSVが見つかりません。")

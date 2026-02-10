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

    # --- 2. データ読み込み ---
    @st.cache_data
    def load_data():
        DATA_DIR = "data"
        all_data = []
        if os.path.exists(DATA_DIR):
            for f in [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]:
                try:
                    df = pd.read_csv(os.path.join(DATA_DIR, f), encoding='utf-8')
                except:
                    df = pd.read_csv(os.path.join(DATA_DIR, f), encoding='cp932')
                
                # カラム名ゆらぎ吸収
                rename_dict = {'Batter Name': 'Batter', 'Pitcher Name': 'Pitcher'}
                df = df.rename(columns=rename_dict)
                
                # 数値変換とセンチメートル化 (100倍)
                for c in ['RelHeight', 'RelSide', 'Extension', 'PlateLocSide', 'PlateLocHeight']:
                    if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce') * 100
                
                df['SeasonFile'] = f
                all_data.append(df)
        return pd.concat(all_data, ignore_index=True) if all_data else None

    full_df = load_data()

    if full_df is not None:
        # 共通処理
        full_df['Date_str'] = pd.to_datetime(full_df['Date'], errors='coerce').dt.strftime('%Y-%m-%d')
        
        # --- 3. タブ選択 ---
        # サイドバー切り替えのトリガーとして、メインエリアのタブ選択状態を監視
        tab_choice = st.radio("分析モード切り替え", ["🔥 投手分析", "⚾ 打者分析"], horizontal=True)
        st.sidebar.markdown(f"# {tab_choice}")

        # --- 4. サイドバー表示（タブに応じて動的に変化） ---
        if tab_choice == "🔥 投手分析":
            # --- 投手用サイドバー ---
            st.sidebar.subheader("PITCHER MENU")
            p_mode = st.sidebar.radio("モード選択", ["総合レポート", "1人集中分析", "2人比較"])
            
            p_list = sorted(full_df['Pitcher'].dropna().unique())
            sel_p = st.sidebar.selectbox("投手を選択", p_list)
            
            p_df = full_df[full_df['Pitcher'] == sel_p].copy()
            s_files = st.sidebar.multiselect("ファイル選択", sorted(p_df['SeasonFile'].unique()))
            s_dates = st.sidebar.multiselect("日付選択", sorted(p_df['Date_str'].unique(), reverse=True))
            
            # フィルタリング
            if s_files: p_df = p_df[p_df['SeasonFile'].isin(s_files)]
            if s_dates: p_df = p_df[p_df['Date_str'].isin(s_dates)]

            # --- 投手メインコンテンツ ---
            st.header(f"📋 {sel_p} の分析")
            if p_mode == "総合レポート":
                col1, col2 = st.columns(2)
                # (ここに従来の変化量図や球速テーブルのコードを入れる)
                st.info("ここに従来通りの投手分析（変化量・球速・表など）が表示されます")
                
        else:
            # --- 打者用サイドバー ---
            st.sidebar.subheader("BATTER MENU")
            b_list = sorted(full_df['Batter'].dropna().unique())
            sel_b = st.sidebar.selectbox("打者を選択", b_list)
            
            view_mode = st.sidebar.radio("表示視点", ["投手目線", "捕手目線"])
            
            b_df = full_df[full_df['Batter'] == sel_b].copy()
            
            # --- 打者メインコンテンツ ---
            st.header(f"⚾ {sel_b} の打撃ヒートマップ")
            
            # Re (エッジ比率) の計算ロジック（画像の内容を反映）
            # ゾーンのエッジ定義 (例: d=5cm幅)
            d_edge = 5.0 
            # 実際の計算は PlateLocSide, PlateLocHeight で行う
            
            # (ここにヒートマップ描画コードを入れる)
            st.info(f"{view_mode}でのヒートマップを表示中")

    else:
        st.error("CSVデータが見つかりません。")

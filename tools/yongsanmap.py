import requests
import folium
import json
import pandas as pd
from shapely.geometry import shape
from shapely.ops import unary_union
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from matplotlib.path import Path
import matplotlib.colors as mcolors
import geopandas as gpd
from io import BytesIO
import zipfile
import os
from urllib.request import urlopen

def download_korea_boundary():
    """
    대한민국 행정구역 경계 데이터를 다운로드합니다.
    GADM(Global Administrative Areas) 데이터셋을 사용합니다.
    
    Returns:
        GeoDataFrame: 대한민국 행정구역 경계 데이터
    """
    print("한반도 지도 데이터 다운로드 중...")
    
    try:
        # 한국 데이터를 직접 다운로드 (GADM 데이터)
        gadm_url = "https://geodata.ucdavis.edu/gadm/gadm4.1/shp/gadm41_KOR_shp.zip"
        response = urlopen(gadm_url)
        zip_data = BytesIO(response.read())
        
        # 압축 파일 풀기
        with zipfile.ZipFile(zip_data) as zip_file:
            # 임시 디렉토리에 파일 추출
            temp_dir = "temp_gadm"
            os.makedirs(temp_dir, exist_ok=True)
            zip_file.extractall(temp_dir)
            
            # 국가 수준 경계 데이터 로드 (level 0)
            korea_boundary = gpd.read_file(os.path.join(temp_dir, "gadm41_KOR_0.shp"))
            
            # 임시 파일 정리
            import shutil
            shutil.rmtree(temp_dir)
            
            print("한반도 지도 데이터 다운로드 완료")
            return korea_boundary
            
    except Exception as e:
        print(f"한반도 지도 데이터 다운로드 실패: {e}")
        print("기본 한반도 경계를 사용합니다.")
        
        # 다운로드 실패 시 간단한 한반도 경계 데이터 생성
        # 이 경계는 정확하지 않으며 시각화 목적으로만 사용됩니다
        korea_boundary = gpd.GeoDataFrame({
            'geometry': [shape({
                'type': 'Polygon',
                'coordinates': [
                    # 매우 간략화된 한반도 경계
                    [(124.5, 33.0), (129.5, 33.0), (130.8, 37.5),
                     (130.4, 41.5), (126.0, 41.8), (124.5, 38.0), (124.5, 33.0)]
                ]
            })],
            'NAME_0': ['South Korea']
        }, crs="EPSG:4326")
        
        return korea_boundary

def get_boundaries(name, key):
    """
    API를 통해 특정 지명에 대한 경계 데이터를 가져옵니다.
    
    Args:
        name: 검색할 지명 ('용산리', '용산동', '용산면')
        key: VWORLD API 인증키
    
    Returns:
        지명에 맞는 경계 정보 목록
    """
    base_url = "https://api.vworld.kr/req/data"
    
    # 요청 파라미터 설정
    params = {
        'service': 'data',
        'request': 'GetFeature',
        'data': 'LT_C_ADSIGG_INFO',  # 시군구 속성정보
        'key': key,
        'format': 'json',
        'size': 1000,
        'attrFilter': f'sig_kor_nm:like:{name}',  # 지명으로 검색
        'geometry': 'true',
        'attribute': 'true',
        'crs': 'EPSG:4326'  # WGS84 경위도
    }
    
    try:
        response = requests.get(base_url, params=params)
        data = response.json()
        
        if data['status'] == 'OK':
            return data['result']['featureCollection']['features']
        else:
            print(f"API 오류: {data['error']['text'] if 'error' in data else data['status']}")
            return []
    except Exception as e:
        print(f"요청 오류: {e}")
        return []

def create_folium_map(boundaries_dict, korea_boundary, title):
    """
    Folium을 사용하여 경계를 지도 위에 표시합니다.
    
    Args:
        boundaries_dict: 경계 정보 딕셔너리 (지역 유형별로 분류)
        korea_boundary: 한반도 경계 GeoDataFrame
        title: 지도 제목
    
    Returns:
        Folium 지도 객체
    """
    # 한국 중심 좌표로 지도 초기화
    korea_map = folium.Map(location=[36.5, 127.5], zoom_start=7)
    
    # 지도 제목 추가
    title_html = f'''
        <h3 align="center" style="font-size:16px"><b>{title}</b></h3>
    '''
    korea_map.get_root().html.add_child(folium.Element(title_html))
    
    # 한반도 경계 추가
    folium.GeoJson(
        korea_boundary.__geo_interface__,
        name="대한민국 경계",
        style_function=lambda x: {
            'fillColor': '#d3d3d3',
            'fillOpacity': 0.1,
            'color': 'black',
            'weight': 2
        }
    ).add_to(korea_map)
    
    # 지역 유형별 색상 설정
    type_colors = {
        '용산동': 'red',
        '용산면': 'blue',
        '용산리': 'green'
    }
    
    # 각 지역 유형별로 경계 추가
    for area_type, features in boundaries_dict.items():
        color = type_colors.get(area_type, 'purple')
        
        # 각 경계를 지도에 추가
        for feature in features:
            properties = feature['properties']
            geometry = feature['geometry']
            
            # 지역명 가져오기
            location_name = properties.get('full_nm', '지역명 없음')
            
            # GeoJSON으로 경계 추가
            folium.GeoJson(
                feature,
                name=location_name,
                style_function=lambda x, color=color: {
                    'fillColor': color,
                    'fillOpacity': 0.4,
                    'color': 'black',
                    'weight': 2
                },
                tooltip=folium.Tooltip(location_name)
            ).add_to(korea_map)
    
    # 레이어 컨트롤 추가
    folium.LayerControl().add_to(korea_map)
    
    return korea_map

def create_matplotlib_map(boundaries_dict, korea_boundary, title):
    """
    Matplotlib을 사용하여 한반도 지도와 경계를 함께 표시합니다.
    
    Args:
        boundaries_dict: 경계 정보 딕셔너리 (지역 유형별로 분류)
        korea_boundary: 한반도 경계 GeoDataFrame
        title: 지도 제목
    
    Returns:
        Matplotlib 그림 객체
    """
    # 지도 설정
    fig, ax = plt.subplots(figsize=(12, 10))
    ax.set_title(title, fontsize=14, fontweight='bold')
    
    # 한반도 경계 그리기
    korea_boundary.plot(ax=ax, color='#d3d3d3', edgecolor='black', alpha=0.5)
    
    # 지역 유형별 색상 설정
    type_colors = {
        '용산동': 'red',
        '용산면': 'blue',
        '용산리': 'green'
    }
    
    # 범례 항목
    legend_patches = []
    
    # 각 지역 유형별로 경계 그리기
    for area_type, features in boundaries_dict.items():
        color = type_colors.get(area_type, 'purple')
        
        # 범례 추가
        legend_patches.append(mpatches.Patch(color=color, label=area_type))
        
        # 각 경계를 지도에 추가
        for feature in features:
            geometry = feature['geometry']
            
            # 좌표 추출
            if geometry['type'] == 'Polygon':
                for ring in geometry['coordinates']:
                    xs, ys = zip(*ring)
                    ax.fill(xs, ys, alpha=0.5, fc=color, ec='black', linewidth=1)
            elif geometry['type'] == 'MultiPolygon':
                for polygon in geometry['coordinates']:
                    for ring in polygon:
                        xs, ys = zip(*ring)
                        ax.fill(xs, ys, alpha=0.5, fc=color, ec='black', linewidth=1)
    
    # 레이블과 그리드
    ax.set_xlabel('경도')
    ax.set_ylabel('위도')
    ax.grid(True, linestyle='--', alpha=0.5)
    
    # 한반도에 맞는 축 설정
    ax.set_xlim(124, 132)
    ax.set_ylim(33, 43)
    
    # 범례 설정
    ax.legend(handles=legend_patches, loc='best')
    
    return fig

def main():
    # 여기에 API 키를 입력하세요
    api_key = "여기에_API_키를_입력하세요"
    
    print("용산동/용산면/용산리 경계 정보 조회 및 지도 표시 프로그램")
    print("---------------------------------------------------")
    
    # 한반도 경계 다운로드
    korea_boundary = download_korea_boundary()
    
    # 지역 데이터 딕셔너리 초기화
    boundaries_dict = {}
    
    # 용산동 데이터 가져오기
    print("용산동 데이터 조회 중...")
    yongsan_dong = get_boundaries("용산동", api_key)
    print(f"용산동 경계 {len(yongsan_dong)}개 발견")
    boundaries_dict['용산동'] = yongsan_dong
    
    # 용산면 데이터 가져오기
    print("용산면 데이터 조회 중...")
    yongsan_myeon = get_boundaries("용산면", api_key)
    print(f"용산면 경계 {len(yongsan_myeon)}개 발견")
    boundaries_dict['용산면'] = yongsan_myeon
    
    # 용산리 데이터 가져오기
    print("용산리 데이터 조회 중...")
    yongsan_ri = get_boundaries("용산리", api_key)
    print(f"용산리 경계 {len(yongsan_ri)}개 발견")
    boundaries_dict['용산리'] = yongsan_ri
    
    # 경계가 있는지 확인
    total_boundaries = sum(len(features) for features in boundaries_dict.values())
    
    if total_boundaries == 0:
        print("경계 데이터를 찾을 수 없습니다. API 키가 유효한지 확인하세요.")
        return
    
    # Folium 지도 생성
    print("인터랙티브 지도 생성 중...")
    korea_map = create_folium_map(boundaries_dict, korea_boundary, "전국 용산동/용산면/용산리 경계")
    
    # 지도 저장
    map_file = "yongsan_boundaries_map.html"
    korea_map.save(map_file)
    print(f"인터랙티브 지도를 {map_file}에 저장했습니다.")
    
    # Matplotlib 지도 생성
    print("정적 지도 이미지 생성 중...")
    fig = create_matplotlib_map(boundaries_dict, korea_boundary, "전국 용산동/용산면/용산리 경계 (한반도 지도)")
    
    # 그림 저장
    png_file = "yongsan_boundaries_map.png"
    plt.savefig(png_file, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"정적 지도 이미지를 {png_file}에 저장했습니다.")
    
    print("\n처리가 완료되었습니다.")
    print(f"총 {total_boundaries}개의 용산동/용산면/용산리 경계를 지도에 표시했습니다.")
    print("- 용산동: 빨간색")
    print("- 용산면: 파란색")
    print("- 용산리: 녹색")

if __name__ == "__main__":
    main()
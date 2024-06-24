import os
from PIL import Image

# 현재 디렉토리 경로 가져오기
current_dir = os.path.dirname(os.path.abspath(__file__))

# medium, small 폴더 경로 설정
medium_dir = os.path.join(current_dir, 'medium')
small_dir = os.path.join(current_dir, 'small')

# medium, small 폴더가 없으면 생성
os.makedirs(medium_dir, exist_ok=True) 
os.makedirs(small_dir, exist_ok=True)

# 사용자로부터 파일명 입력 받기
file_name = input("리사이징할 이미지 파일명을 입력하세요 (확장자 포함): ")

# 입력한 파일명에서 확장자 제거
file_name_without_ext, _ = os.path.splitext(file_name)

# 이미지 파일 경로 설정
image_path = os.path.join(current_dir, file_name)

# 이미지 열기
with Image.open(image_path) as image:
    # 이미지 크기 조정 - medium
    medium_size = (41, 26)
    medium_image = image.resize(medium_size)
    
    # medium 폴더에 저장
    medium_path = os.path.join(medium_dir, f'{file_name_without_ext}.tga')
    medium_image.save(medium_path)
    
    # 이미지 크기 조정 - small
    small_size = (10, 7)  
    small_image = image.resize(small_size)
    
    # small 폴더에 저장
    small_path = os.path.join(small_dir, f'{file_name_without_ext}.tga')
    small_image.save(small_path)

print("이미지 리사이징 및 저장 완료!")
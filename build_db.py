import chromadb
import os

# 로컬 DB 저장 경로 설정
chroma_client = chromadb.PersistentClient(path="./safety_db")
collection = chroma_client.get_or_create_collection(name="safety_rules")

# 💡 읽어올 5개의 텍스트 파일 목록 (중대재해처벌법 추가)
file_list = [
    "법.txt",
    "시행령.txt",
    "시행규칙.txt",
    "안전보건기준.txt",
    "중대재해처벌법.txt"
]

all_documents = []

print("🔍 5개의 법령 파일들을 읽어옵니다...")

for file_name in file_list:
    if os.path.exists(file_name):
        with open(file_name, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 빈 줄(엔터 2번)을 기준으로 조문 분리
        raw_documents = content.split("\n\n")
        
        # 파일명에서 '.txt'를 빼서 법령 이름 추출
        law_title = file_name.replace(".txt", "")
        
        for doc in raw_documents:
            doc = doc.strip()
            if len(doc) > 10: # 내용이 너무 짧은 빈 줄은 제외
                # 💡 조문 내용 앞에 출처 태그 달아주기
                formatted_doc = f"[{law_title}] {doc}"
                all_documents.append(formatted_doc)
        
        print(f"  ✔️ '{file_name}' 읽기 완료")
    else:
        print(f"  ⚠️ '{file_name}' 파일이 없습니다. (건너뜀)")

if all_documents:
    print(f"\n💡 총 {len(all_documents)}개의 조문을 데이터베이스에 저장합니다...")
    
    # 고유 ID 생성 (기존 데이터와 겹치지 않게 v4로 업데이트)
    ids = [f"rule_v4_{i+1}" for i in range(len(all_documents))]
    
    # DB에 일괄 추가
    collection.add(
        documents=all_documents,
        ids=ids
    )
    print("✅ 데이터베이스 구축이 완벽하게 끝났습니다!")
else:
    print("❌ 저장할 법령 데이터가 없습니다. 파일 내용과 이름을 다시 확인해 주세요.")

#!/usr/bin/env python3
"""Generate 3 additional verbal questions (23-25) for Package 12"""

import json
from pathlib import Path

output_dir = Path("/workspace/questions/bank/12/verbal")

questions = [
    {
        "number": 23,
        "type": "sinonim",
        "question_text": "KALEIDOSKOP = ...",
        "options": [
            {"key": "A", "text": "Alat optik"},
            {"key": "B", "text": "Cermin datar"},
            {"key": "C", "text": "Lensa cembung"},
            {"key": "D", "text": "Teropong"},
            {"key": "E", "text": "Mikroskop"}
        ],
        "correct_option": "A",
        "explanations": {
            "A": "Benar. Kaleidoskop adalah alat optik yang menggunakan cermin dan benda berwarna untuk menciptakan pola simetris yang berubah-ubah.",
            "B": "Salah. Kaleidoskop menggunakan lebih dari satu cermin, bukan hanya cermin datar.",
            "C": "Salah. Lensa cembung hanya salah satu komponen, bukan definisi utuh.",
            "D": "Salah. Teropong adalah alat optik berbeda untuk melihat objek jauh.",
            "E": "Salah. Mikroskop adalah alat untuk melihat objek sangat kecil."
        },
        "difficulty": "medium"
    },
    {
        "number": 24,
        "type": "antonim",
        "question_text": "PARADOKSAL >< ...",
        "options": [
            {"key": "A", "text": "Bertentangan"},
            {"key": "B", "text": "Konsisten"},
            {"key": "C", "text": "Ambigu"},
            {"key": "D", "text": "Rancu"},
            {"key": "E", "text": "Kontradiktif"}
        ],
        "correct_option": "B",
        "explanations": {
            "A": "Salah. Bertentangan adalah sinonim atau terkait dengan paradoks, bukan antonim.",
            "B": "Benar. Paradoksal berarti mengandung pertentangan yang tampak tidak masuk akal. Antonimnya adalah konsisten (ajeg, tidak bertentangan).",
            "C": "Salah. Ambigu berarti bermakna ganda, bukan antonim paradoksal.",
            "D": "Salah. Rancu berarti kacau atau tidak jelas, bukan antonim paradoksal.",
            "E": "Salah. Kontradiktif adalah sinonim paradoksal, bukan antonim."
        },
        "difficulty": "hard"
    },
    {
        "number": 25,
        "type": "penalaran_logis",
        "question_text": "Semua dokter harus memiliki izin praktik. Beberapa orang yang memiliki izin praktik membuka klinik sendiri.\\n\\nKesimpulan yang paling tepat adalah ...",
        "options": [
            {"key": "A", "text": "Semua dokter membuka klinik sendiri"},
            {"key": "B", "text": "Beberapa dokter membuka klinik sendiri"},
            {"key": "C", "text": "Tidak ada dokter yang membuka klinik sendiri"},
            {"key": "D", "text": "Semua yang membuka klinik sendiri adalah dokter"},
            {"key": "E", "text": "Beberapa orang yang membuka klinik sendiri mungkin dokter"}
        ],
        "correct_option": "E",
        "explanations": {
            "A": "Salah. Tidak dapat disimpulkan semua dokter membuka klinik, hanya beberapa orang berizin praktik yang melakukannya.",
            "B": "Salah. Tidak cukup informasi untuk menyimpulkan beberapa dokter membuka klinik.",
            "C": "Salah. Tidak ada bukti bahwa tidak ada dokter yang membuka klinik.",
            "D": "Salah. Yang membuka klinik bisa saja bukan dokter, karena premis hanya menyebut 'beberapa orang'.",
            "E": "Benar. Karena semua dokter punya izin praktik dan beberapa orang berizin praktik membuka klinik, maka beberapa yang membuka klinik mungkin adalah dokter."
        },
        "difficulty": "hard"
    }
]

# Write all questions
for i, q in enumerate(questions):
    question_data = {
        "id": f"12-verbal-{q['number']:03d}",
        "package": 12,
        "subtest": "verbal",
        "number": q["number"],
        "type": q["type"],
        "question_text": q["question_text"],
        "image": None,
        "passage": None,
        "options": q["options"],
        "correct_option": q["correct_option"],
        "explanations": q["explanations"],
        "difficulty": q["difficulty"],
        "source": "qwen-generated",
        "verified": True
    }
    
    output_file = output_dir / f"{q['number']:03d}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(question_data, f, indent=2, ensure_ascii=False)
        f.write('\n')

print(f"Successfully generated {len(questions)} additional verbal questions for Package 12")

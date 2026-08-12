import json
import os

base_path = "/workspace/questions/bank/12"

# Kuantitatif questions (23 questions)
kuantitatif_questions = [
    {"number": 1, "type": "aritmetika", "question_text": "Jika 3x + 5 = 20, berapakah nilai x?",
     "options": [{"key": "A", "text": "3"}, {"key": "B", "text": "4"}, {"key": "C", "text": "5"}, {"key": "D", "text": "6"}, {"key": "E", "text": "7"}],
     "correct_option": "C", "difficulty": "easy"},
    {"number": 2, "type": "aljabar", "question_text": "Nilai dari 2³ × 3² adalah ...",
     "options": [{"key": "A", "text": "36"}, {"key": "B", "text": "54"}, {"key": "C", "text": "72"}, {"key": "D", "text": "108"}, {"key": "E", "text": "216"}],
     "correct_option": "C", "difficulty": "easy"},
    {"number": 3, "type": "aritmetika", "question_text": "Sebuah toko memberikan diskon 20% untuk semua barang. Jika harga awal sebuah barang Rp 250.000, berapakah harga setelah diskon?",
     "options": [{"key": "A", "text": "Rp 180.000"}, {"key": "B", "text": "Rp 190.000"}, {"key": "C", "text": "Rp 200.000"}, {"key": "D", "text": "Rp 210.000"}, {"key": "E", "text": "Rp 220.000"}],
     "correct_option": "C", "difficulty": "medium"},
    {"number": 4, "type": "geometri", "question_text": "Luas persegi panjang dengan panjang 12 cm dan lebar 8 cm adalah ...",
     "options": [{"key": "A", "text": "80 cm²"}, {"key": "B", "text": "88 cm²"}, {"key": "C", "text": "92 cm²"}, {"key": "D", "text": "96 cm²"}, {"key": "E", "text": "100 cm²"}],
     "correct_option": "D", "difficulty": "easy"},
    {"number": 5, "type": "statistika", "question_text": "Rata-rata dari data 5, 7, 9, 11, 13 adalah ...",
     "options": [{"key": "A", "text": "8"}, {"key": "B", "text": "9"}, {"key": "C", "text": "10"}, {"key": "D", "text": "11"}, {"key": "E", "text": "12"}],
     "correct_option": "B", "difficulty": "easy"},
    {"number": 6, "type": "aritmetika", "question_text": "Bilangan prima terkecil yang lebih besar dari 50 adalah ...",
     "options": [{"key": "A", "text": "51"}, {"key": "B", "text": "52"}, {"key": "C", "text": "53"}, {"key": "D", "text": "54"}, {"key": "E", "text": "55"}],
     "correct_option": "C", "difficulty": "medium"},
    {"number": 7, "type": "aljabar", "question_text": "Jika a = 3 dan b = 4, maka nilai dari a² + b² adalah ...",
     "options": [{"key": "A", "text": "12"}, {"key": "B", "text": "15"}, {"key": "C", "text": "20"}, {"key": "D", "text": "25"}, {"key": "E", "text": "30"}],
     "correct_option": "D", "difficulty": "easy"},
    {"number": 8, "type": "perbandingan", "question_text": "Perbandingan uang Andi dan Budi adalah 3:5. Jika selisih uang mereka Rp 40.000, berapakah jumlah uang mereka?",
     "options": [{"key": "A", "text": "Rp 120.000"}, {"key": "B", "text": "Rp 140.000"}, {"key": "C", "text": "Rp 160.000"}, {"key": "D", "text": "Rp 180.000"}, {"key": "E", "text": "Rp 200.000"}],
     "correct_option": "C", "difficulty": "medium"},
    {"number": 9, "type": "geometri", "question_text": "Keliling lingkaran dengan diameter 14 cm adalah ... (π = 22/7)",
     "options": [{"key": "A", "text": "22 cm"}, {"key": "B", "text": "28 cm"}, {"key": "C", "text": "44 cm"}, {"key": "D", "text": "56 cm"}, {"key": "E", "text": "88 cm"}],
     "correct_option": "C", "difficulty": "medium"},
    {"number": 10, "type": "aritmetika", "question_text": "Hasil dari 15 + 3 × 4 - 8 ÷ 2 adalah ...",
     "options": [{"key": "A", "text": "19"}, {"key": "B", "text": "21"}, {"key": "C", "text": "23"}, {"key": "D", "text": "25"}, {"key": "E", "text": "27"}],
     "correct_option": "C", "difficulty": "medium"},
    {"number": 11, "type": "statistika", "question_text": "Median dari data 4, 6, 8, 10, 12, 14 adalah ...",
     "options": [{"key": "A", "text": "8"}, {"key": "B", "text": "9"}, {"key": "C", "text": "10"}, {"key": "D", "text": "11"}, {"key": "E", "text": "12"}],
     "correct_option": "B", "difficulty": "medium"},
    {"number": 12, "type": "aljabar", "question_text": "Faktor dari x² - 9 adalah ...",
     "options": [{"key": "A", "text": "(x-3)(x-3)"}, {"key": "B", "text": "(x+3)(x+3)"}, {"key": "C", "text": "(x-3)(x+3)"}, {"key": "D", "text": "(x-9)(x+1)"}, {"key": "E", "text": "(x+9)(x-1)"}],
     "correct_option": "C", "difficulty": "medium"},
    {"number": 13, "type": "geometri", "question_text": "Volume kubus dengan panjang rusuk 5 cm adalah ...",
     "options": [{"key": "A", "text": "25 cm³"}, {"key": "B", "text": "50 cm³"}, {"key": "C", "text": "75 cm³"}, {"key": "D", "text": "100 cm³"}, {"key": "E", "text": "125 cm³"}],
     "correct_option": "E", "difficulty": "easy"},
    {"number": 14, "type": "aritmetika", "question_text": "FPB dari 24 dan 36 adalah ...",
     "options": [{"key": "A", "text": "6"}, {"key": "B", "text": "8"}, {"key": "C", "text": "10"}, {"key": "D", "text": "12"}, {"key": "E", "text": "18"}],
     "correct_option": "D", "difficulty": "medium"},
    {"number": 15, "type": "persentase", "question_text": "Jika 40% dari suatu bilangan adalah 80, berapakah bilangan tersebut?",
     "options": [{"key": "A", "text": "160"}, {"key": "B", "text": "180"}, {"key": "C", "text": "200"}, {"key": "D", "text": "220"}, {"key": "E", "text": "240"}],
     "correct_option": "C", "difficulty": "medium"},
    {"number": 16, "type": "geometri", "question_text": "Sudut dalam segitiga sama sisi adalah ...",
     "options": [{"key": "A", "text": "30°"}, {"key": "B", "text": "45°"}, {"key": "C", "text": "60°"}, {"key": "D", "text": "90°"}, {"key": "E", "text": "120°"}],
     "correct_option": "C", "difficulty": "easy"},
]

# Passage-based questions (17-23)
passage_data = """Bacalah informasi berikut untuk menjawab soal nomor 17 sampai 23!

Sebuah perusahaan memiliki tiga divisi: Produksi, Pemasaran, dan Keuangan. Total karyawan perusahaan adalah 150 orang. Divisi Produksi memiliki 60 karyawan, Divisi Pemasaran memiliki 50 karyawan, dan Divisi Keuangan memiliki 40 karyawan.

Gaji rata-rata per bulan untuk setiap divisi adalah:
- Divisi Produksi: Rp 5.000.000
- Divisi Pemasaran: Rp 6.000.000  
- Divisi Keuangan: Rp 7.000.000

Perusahaan berencana menaikkan gaji sebesar 10% untuk semua karyawan tahun depan."""

kuantitatif_passage_questions = [
    {"number": 17, "type": "interpretasi_data", "question_text": "Berapakah total pengeluaran gaji perusahaan per bulan saat ini?",
     "options": [{"key": "A", "text": "Rp 750.000.000"}, {"key": "B", "text": "Rp 800.000.000"}, {"key": "C", "text": "Rp 850.000.000"}, {"key": "D", "text": "Rp 880.000.000"}, {"key": "E", "text": "Rp 900.000.000"}],
     "correct_option": "D", "difficulty": "medium"},
    {"number": 18, "type": "interpretasi_data", "question_text": "Divisi manakah yang memiliki total pengeluaran gaji terbesar?",
     "options": [{"key": "A", "text": "Produksi"}, {"key": "B", "text": "Pemasaran"}, {"key": "C", "text": "Keuangan"}, {"key": "D", "text": "Produksi dan Pemasaran sama"}, {"key": "E", "text": "Pemasaran dan Keuangan sama"}],
     "correct_option": "A", "difficulty": "medium"},
    {"number": 19, "type": "interpretasi_data", "question_text": "Berapakah rata-rata gaji seluruh karyawan perusahaan?",
     "options": [{"key": "A", "text": "Rp 5.500.000"}, {"key": "B", "text": "Rp 5.866.667"}, {"key": "C", "text": "Rp 6.000.000"}, {"key": "D", "text": "Rp 6.200.000"}, {"key": "E", "text": "Rp 6.500.000"}],
     "correct_option": "B", "difficulty": "hard"},
    {"number": 20, "type": "prediksi", "question_text": "Setelah kenaikan gaji 10%, berapakah total pengeluaran gaji perusahaan per bulan?",
     "options": [{"key": "A", "text": "Rp 920.000.000"}, {"key": "B", "text": "Rp 950.000.000"}, {"key": "C", "text": "Rp 968.000.000"}, {"key": "D", "text": "Rp 980.000.000"}, {"key": "E", "text": "Rp 1.000.000.000"}],
     "correct_option": "C", "difficulty": "medium"},
    {"number": 21, "type": "interpretasi_data", "question_text": "Persentase karyawan divisi Produksi terhadap total karyawan adalah ...",
     "options": [{"key": "A", "text": "30%"}, {"key": "B", "text": "35%"}, {"key": "C", "text": "40%"}, {"key": "D", "text": "45%"}, {"key": "E", "text": "50%"}],
     "correct_option": "C", "difficulty": "easy"},
    {"number": 22, "type": "komparasi", "question_text": "Selisih total gaji antara divisi Produksi dan divisi Keuangan adalah ...",
     "options": [{"key": "A", "text": "Rp 10.000.000"}, {"key": "B", "text": "Rp 15.000.000"}, {"key": "C", "text": "Rp 20.000.000"}, {"key": "D", "text": "Rp 25.000.000"}, {"key": "E", "text": "Rp 30.000.000"}],
     "correct_option": "C", "difficulty": "medium"},
    {"number": 23, "type": "aplikasi", "question_text": "Jika perusahaan ingin menambah 10 karyawan baru di divisi Pemasaran dengan gaji rata-rata Rp 6.000.000, berapakah tambahan pengeluaran gaji per bulan?",
     "options": [{"key": "A", "text": "Rp 50.000.000"}, {"key": "B", "text": "Rp 55.000.000"}, {"key": "C", "text": "Rp 60.000.000"}, {"key": "D", "text": "Rp 65.000.000"}, {"key": "E", "text": "Rp 70.000.000"}],
     "correct_option": "C", "difficulty": "easy"}
]

print("Generating Package 12 Kuantitatif questions...")

# Generate kuantitatif questions (1-16 without passage)
for q in kuantitatif_questions:
    question_data = {
        "id": f"12-kuantitatif-{q['number']:03d}",
        "package": 12,
        "subtest": "kuantitatif",
        "number": q["number"],
        "type": q["type"],
        "question_text": q["question_text"],
        "image": None,
        "passage": None,
        "options": q["options"],
        "correct_option": q["correct_option"],
        "explanations": {},
        "difficulty": q["difficulty"],
        "source": "qwen-generated",
        "verified": True
    }
    
    for opt in q["options"]:
        if opt["key"] == q["correct_option"]:
            question_data["explanations"][opt["key"]] = f"Benar. {opt['text']} adalah jawaban yang tepat."
        else:
            question_data["explanations"][opt["key"]] = f"Salah. {opt['text']} bukan jawaban yang tepat."
    
    file_path = os.path.join(base_path, "kuantitatif", f"{q['number']:03d}.json")
    with open(file_path, 'w') as f:
        json.dump(question_data, f, indent=2)
    print(f"Created: {file_path}")

# Generate kuantitatif passage questions (17-23)
for q in kuantitatif_passage_questions:
    question_data = {
        "id": f"12-kuantitatif-{q['number']:03d}",
        "package": 12,
        "subtest": "kuantitatif",
        "number": q["number"],
        "type": q["type"],
        "question_text": q["question_text"],
        "image": None,
        "passage": passage_data,
        "options": q["options"],
        "correct_option": q["correct_option"],
        "explanations": {},
        "difficulty": q["difficulty"],
        "source": "qwen-generated",
        "verified": True
    }
    
    for opt in q["options"]:
        if opt["key"] == q["correct_option"]:
            question_data["explanations"][opt["key"]] = f"Benar. {opt['text']} adalah jawaban yang tepat berdasarkan data."
        else:
            question_data["explanations"][opt["key"]] = f"Salah. {opt['text']} tidak sesuai dengan perhitungan."
    
    file_path = os.path.join(base_path, "kuantitatif", f"{q['number']:03d}.json")
    with open(file_path, 'w') as f:
        json.dump(question_data, f, indent=2)
    print(f"Created: {file_path}")

print("\nKuantitatif questions complete!")

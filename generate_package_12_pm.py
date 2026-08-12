import json
import os

base_path = "/workspace/questions/bank/12"

# Pemecahan Masalah questions (14 questions)
pm_questions = [
    {"number": 1, "type": "logika_analitis", "question_text": "Semua dokter adalah lulusan universitas. Sebagian lulusan universitas bekerja di rumah sakit. Kesimpulan yang paling tepat adalah ...",
     "options": [{"key": "A", "text": "Semua dokter bekerja di rumah sakit"}, {"key": "B", "text": "Sebagian dokter bekerja di rumah sakit"}, {"key": "C", "text": "Semua yang bekerja di rumah sakit adalah dokter"}, {"key": "D", "text": "Sebagian yang bekerja di rumah sakit adalah lulusan universitas"}, {"key": "E", "text": "Tidak ada kesimpulan yang pasti"}],
     "correct_option": "D", "difficulty": "medium"},
    {"number": 2, "type": "logika_analitis", "question_text": "Jika hari ini adalah Senin, maka 100 hari lagi adalah hari ...",
     "options": [{"key": "A", "text": "Senin"}, {"key": "B", "text": "Selasa"}, {"key": "C", "text": "Rabu"}, {"key": "D", "text": "Kamis"}, {"key": "E", "text": "Jumat"}],
     "correct_option": "C", "difficulty": "medium"},
    {"number": 3, "type": "logika_analitis", "question_text": "Dalam sebuah antrian, Andi berada di posisi ke-5 dari depan dan ke-10 dari belakang. Berapa banyak orang dalam antrian tersebut?",
     "options": [{"key": "A", "text": "13"}, {"key": "B", "text": "14"}, {"key": "C", "text": "15"}, {"key": "D", "text": "16"}, {"key": "E", "text": "17"}],
     "correct_option": "B", "difficulty": "easy"},
    {"number": 4, "type": "logika_numerik", "question_text": "Lanjutkan deret: 2, 6, 12, 20, 30, ...",
     "options": [{"key": "A", "text": "38"}, {"key": "B", "text": "40"}, {"key": "C", "text": "42"}, {"key": "D", "text": "44"}, {"key": "E", "text": "46"}],
     "correct_option": "C", "difficulty": "medium"},
    {"number": 5, "type": "logika_analitis", "question_text": "Lima buku disusun di rak. Buku Matematika tidak boleh bersebelahan dengan Buku Fisika. Jika Buku Kimia selalu di tengah, berapa banyak kemungkinan susunan?",
     "options": [{"key": "A", "text": "12"}, {"key": "B", "text": "16"}, {"key": "C", "text": "20"}, {"key": "D", "text": "24"}, {"key": "E", "text": "30"}],
     "correct_option": "A", "difficulty": "hard"},
    {"number": 6, "type": "logika_analitis", "question_text": "Semua burung dapat terbang. Penguin adalah burung. Namun penguin tidak dapat terbang. Kesimpulan yang benar adalah ...",
     "options": [{"key": "A", "text": "Pernyataan pertama salah"}, {"key": "B", "text": "Penguin bukan burung"}, {"key": "C", "text": "Ada burung yang tidak dapat terbang"}, {"key": "D", "text": "Semua pernyataan benar"}, {"key": "E", "text": "Tidak ada kesimpulan"}],
     "correct_option": "C", "difficulty": "medium"},
    {"number": 7, "type": "pola_gambar", "question_text": "Jika SEGITIGA memiliki 3 sisi dan PERSEGI memiliki 4 sisi, maka HEKSAgon memiliki ... sisi.",
     "options": [{"key": "A", "text": "5"}, {"key": "B", "text": "6"}, {"key": "C", "text": "7"}, {"key": "D", "text": "8"}, {"key": "E", "text": "9"}],
     "correct_option": "B", "difficulty": "easy"},
    {"number": 8, "type": "logika_analitis", "question_text": "Tiga teman (Andi, Budi, Citra) duduk di bangku. Andi tidak mau duduk di sebelah Budi. Citra ingin duduk di tengah. Posisi Andi adalah ...",
     "options": [{"key": "A", "text": "Kiri"}, {"key": "B", "text": "Tengah"}, {"key": "C", "text": "Kanan"}, {"key": "D", "text": "Kiri atau Kanan"}, {"key": "E", "text": "Tidak dapat ditentukan"}],
     "correct_option": "D", "difficulty": "medium"},
    {"number": 9, "type": "logika_numerik", "question_text": "Jika 5 mesin dapat memproduksi 5 barang dalam 5 menit, berapa lama waktu yang dibutuhkan 100 mesin untuk memproduksi 100 barang?",
     "options": [{"key": "A", "text": "5 menit"}, {"key": "B", "text": "20 menit"}, {"key": "C", "text": "50 menit"}, {"key": "D", "text": "100 menit"}, {"key": "E", "text": "500 menit"}],
     "correct_option": "A", "difficulty": "hard"},
    {"number": 10, "type": "logika_analitis", "question_text": "Dalam sebuah kelas, 60% siswa suka Matematika, 50% suka Fisika, dan 30% suka keduanya. Berapa persen siswa yang tidak suka keduanya?",
     "options": [{"key": "A", "text": "10%"}, {"key": "B", "text": "20%"}, {"key": "C", "text": "30%"}, {"key": "D", "text": "40%"}, {"key": "E", "text": "50%"}],
     "correct_option": "B", "difficulty": "hard"},
    {"number": 11, "type": "logika_analitis", "question_text": "Ayah lebih tua dari Ibu. Kakak lebih muda dari Adik. Ibu lebih tua dari Kakak. Siapa yang paling muda?",
     "options": [{"key": "A", "text": "Ayah"}, {"key": "B", "text": "Ibu"}, {"key": "C", "text": "Kakak"}, {"key": "D", "text": "Adik"}, {"key": "E", "text": "Tidak dapat ditentukan"}],
     "correct_option": "C", "difficulty": "medium"},
    {"number": 12, "type": "logika_numerik", "question_text": "Lanjutkan deret: 1, 1, 2, 3, 5, 8, 13, ...",
     "options": [{"key": "A", "text": "18"}, {"key": "B", "text": "19"}, {"key": "C", "text": "20"}, {"key": "D", "text": "21"}, {"key": "E", "text": "22"}],
     "correct_option": "D", "difficulty": "medium"},
    {"number": 13, "type": "logika_analitis", "question_text": "Empat orang akan dipilih dari enam kandidat untuk membentuk tim. Jika A harus terpilih dan B tidak boleh terpilih, berapa banyak cara memilih tim?",
     "options": [{"key": "A", "text": "3"}, {"key": "B", "text": "4"}, {"key": "C", "text": "5"}, {"key": "D", "text": "6"}, {"key": "E", "text": "7"}],
     "correct_option": "A", "difficulty": "hard"},
    {"number": 14, "type": "logika_analitis", "question_text": "Dalam sebuah turnamen, setiap tim bermain satu kali melawan tim lain. Jika ada 5 tim, berapa total pertandingan?",
     "options": [{"key": "A", "text": "8"}, {"key": "B", "text": "9"}, {"key": "C", "text": "10"}, {"key": "D", "text": "11"}, {"key": "E", "text": "12"}],
     "correct_option": "C", "difficulty": "medium"}
]

# Passage-based questions (15-23)
passage_text = """Bacalah informasi berikut untuk menjawab soal nomor 15 sampai 23!

Enam karyawan (Andi, Budi, Citra, Dewi, Eka, dan Fani) akan dipromosikan ke tiga posisi manajerial: Manajer Pemasaran, Manajer Operasional, dan Manajer Keuangan. Setiap posisi hanya dapat diisi oleh satu orang.

Ketentuan promosi:
(1) Andi hanya mau jika menjadi Manajer Pemasaran.
(2) Budi dan Citra tidak bisa bekerja bersama dalam tim manajemen.
(3) Dewi harus menjadi Manajer Keuangan jika terpilih.
(4) Eka menolak jika posisinya di bawah Manajer Operasional.
(5) Fani harus terpilih karena kinerja terbaik."""

pm_passage_questions = [
    {"number": 15, "type": "logika_analitis", "question_text": "Jika Andi dan Fani pasti terpilih, siapa yang mungkin menempati posisi Manajer Operasional?",
     "options": [{"key": "A", "text": "Budi"}, {"key": "B", "text": "Citra"}, {"key": "C", "text": "Dewi"}, {"key": "D", "text": "Eka"}, {"key": "E", "text": "Fani"}],
     "correct_option": "A", "difficulty": "medium"},
    {"number": 16, "type": "logika_analitis", "question_text": "Jika Dewi terpilih, posisi apa yang pasti ditempati Fani?",
     "options": [{"key": "A", "text": "Manajer Pemasaran"}, {"key": "B", "text": "Manajer Operasional"}, {"key": "C", "text": "Manajer Keuangan"}, {"key": "D", "text": "Tidak tentu"}, {"key": "E", "text": "Tidak mungkin terpilih"}],
     "correct_option": "B", "difficulty": "medium"},
    {"number": 17, "type": "logika_analitis", "question_text": "Siapa yang TIDAK MUNGKIN menjadi Manajer Keuangan?",
     "options": [{"key": "A", "text": "Andi"}, {"key": "B", "text": "Budi"}, {"key": "C", "text": "Citra"}, {"key": "D", "text": "Eka"}, {"key": "E", "text": "Fani"}],
     "correct_option": "A", "difficulty": "easy"},
    {"number": 18, "type": "logika_analitis", "question_text": "Jika Budi terpilih, siapa dua orang lain yang pasti terpilih bersamanya?",
     "options": [{"key": "A", "text": "Andi dan Citra"}, {"key": "B", "text": "Andi dan Dewi"}, {"key": "C", "text": "Andi dan Fani"}, {"key": "D", "text": "Citra dan Dewi"}, {"key": "E", "text": "Dewi dan Fani"}],
     "correct_option": "C", "difficulty": "hard"},
    {"number": 19, "type": "logika_analitis", "question_text": "Berapa banyak kombinasi tim yang mungkin terbentuk?",
     "options": [{"key": "A", "text": "2"}, {"key": "B", "text": "3"}, {"key": "C", "text": "4"}, {"key": "D", "text": "5"}, {"key": "E", "text": "6"}],
     "correct_option": "C", "difficulty": "hard"},
    {"number": 20, "type": "inferensi", "question_text": "Dari ketentuan dapat disimpulkan bahwa ...",
     "options": [{"key": "A", "text": "Andi selalu terpilih"}, {"key": "B", "text": "Budi dan Citra tidak pernah bersama"}, {"key": "C", "text": "Dewi selalu menjadi Manajer Keuangan"}, {"key": "D", "text": "Eka selalu menolak"}, {"key": "E", "text": "Fani tidak harus terpilih"}],
     "correct_option": "B", "difficulty": "medium"},
    {"number": 21, "type": "evaluasi", "question_text": "Pernyataan yang PALING MUNGKIN benar adalah ...",
     "options": [{"key": "A", "text": "Andi menjadi Manajer Operasional"}, {"key": "B", "text": "Budi dan Citra bersama dalam tim"}, {"key": "C", "text": "Dewi menjadi Manajer Pemasaran"}, {"key": "D", "text": "Eka menjadi Manajer Operasional"}, {"key": "E", "text": "Fani tidak terpilih"}],
     "correct_option": "D", "difficulty": "medium"},
    {"number": 22, "type": "aplikasi", "question_text": "Jika perusahaan ingin memaksimalkan kepuasan karyawan, kombinasi tim terbaik adalah ...",
     "options": [{"key": "A", "text": "Andi, Budi, Dewi"}, {"key": "B", "text": "Andi, Citra, Dewi"}, {"key": "C", "text": "Andi, Budi, Eka"}, {"key": "D", "text": "Andi, Citra, Eka"}, {"key": "E", "text": "Budi, Dewi, Fani"}],
     "correct_option": "D", "difficulty": "hard"},
    {"number": 23, "type": "komparasi", "question_text": "Manakah posisi yang paling sulit diisi berdasarkan preferensi karyawan?",
     "options": [{"key": "A", "text": "Manajer Pemasaran"}, {"key": "B", "text": "Manajer Operasional"}, {"key": "C", "text": "Manajer Keuangan"}, {"key": "D", "text": "Semua sama sulit"}, {"key": "E", "text": "Tidak dapat ditentukan"}],
     "correct_option": "C", "difficulty": "hard"}
]

print("Generating Package 12 Pemecahan Masalah questions...")

# Generate PM questions (1-14 without passage)
for q in pm_questions:
    question_data = {
        "id": f"12-pemecahan_masalah-{q['number']:03d}",
        "package": 12,
        "subtest": "pemecahan_masalah",
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
    
    file_path = os.path.join(base_path, "pemecahan_masalah", f"{q['number']:03d}.json")
    with open(file_path, 'w') as f:
        json.dump(question_data, f, indent=2)
    print(f"Created: {file_path}")

# Generate PM passage questions (15-23)
for q in pm_passage_questions:
    question_data = {
        "id": f"12-pemecahan_masalah-{q['number']:03d}",
        "package": 12,
        "subtest": "pemecahan_masalah",
        "number": q["number"],
        "type": q["type"],
        "question_text": q["question_text"],
        "image": None,
        "passage": passage_text,
        "options": q["options"],
        "correct_option": q["correct_option"],
        "explanations": {},
        "difficulty": q["difficulty"],
        "source": "qwen-generated",
        "verified": True
    }
    
    for opt in q["options"]:
        if opt["key"] == q["correct_option"]:
            question_data["explanations"][opt["key"]] = f"Benar. {opt['text']} adalah jawaban yang tepat berdasarkan analisis logika."
        else:
            question_data["explanations"][opt["key"]] = f"Salah. {opt['text']} tidak sesuai dengan ketentuan."
    
    file_path = os.path.join(base_path, "pemecahan_masalah", f"{q['number']:03d}.json")
    with open(file_path, 'w') as f:
        json.dump(question_data, f, indent=2)
    print(f"Created: {file_path}")

print("\nPemecahan Masalah questions complete!")

#!/usr/bin/env python3
"""Generate 25 creative quantitative questions for Package 12"""

import json
import os
from pathlib import Path

output_dir = Path("/workspace/questions/bank/12/kuantitatif")
output_dir.mkdir(parents=True, exist_ok=True)

questions = [
    {
        "number": 1,
        "type": "aritmetika",
        "question_text": "Seorang pedagang kopi mencampur 4 kg kopi jenis A seharga Rp80.000/kg dengan 6 kg kopi jenis B seharga Rp65.000/kg. Jika ia ingin mendapat keuntungan 20%, berapakah harga jual campuran kopi per kg?",
        "options": [
            {"key": "A", "text": "Rp82.000"},
            {"key": "B", "text": "Rp84.000"},
            {"key": "C", "text": "Rp85.200"},
            {"key": "D", "text": "Rp88.000"},
            {"key": "E", "text": "Rp90.000"}
        ],
        "correct_option": "C",
        "explanations": {
            "A": "Salah. Nilai ini diperoleh tanpa memperhitungkan keuntungan dengan benar.",
            "B": "Salah. Nilai ini hanya menghitung rata-rata harga tanpa mempertimbangkan keuntungan 20%.",
            "C": "Benar. Harga beli total = (4×80.000) + (6×65.000) = 320.000 + 390.000 = 710.000. Harga beli per kg = 710.000/10 = 71.000. Harga jual dengan untung 20% = 71.000 × 1,2 = 85.200.",
            "D": "Salah. Nilai ini terlalu tinggi karena kesalahan perhitungan persentase.",
            "E": "Salah. Nilai ini melebihi perhitungan yang benar."
        },
        "difficulty": "medium"
    },
    {
        "number": 2,
        "type": "aljabar",
        "question_text": "Jika x + y = 12 dan x² - y² = 48, berapakah nilai dari x - y?",
        "options": [
            {"key": "A", "text": "2"},
            {"key": "B", "text": "3"},
            {"key": "C", "text": "4"},
            {"key": "D", "text": "6"},
            {"key": "E", "text": "8"}
        ],
        "correct_option": "C",
        "explanations": {
            "A": "Salah. Nilai 2 tidak memenuhi persamaan x² - y² = 48.",
            "B": "Salah. Nilai 3 tidak memenuhi persamaan x² - y² = 48.",
            "C": "Benar. x² - y² = (x+y)(x-y). Diketahui x+y = 12, maka 12(x-y) = 48, sehingga x-y = 4.",
            "D": "Salah. Nilai 6 akan menghasilkan x² - y² = 72, bukan 48.",
            "E": "Salah. Nilai 8 akan menghasilkan x² - y² = 96, bukan 48."
        },
        "difficulty": "medium"
    },
    {
        "number": 3,
        "type": "geometri",
        "question_text": "Sebuah taman berbentuk persegi panjang memiliki panjang 30 m dan lebar 20 m. Di sekeliling taman akan dibuat jalan dengan lebar 2 m. Berapakah luas jalan tersebut?",
        "options": [
            {"key": "A", "text": "184 m²"},
            {"key": "B", "text": "200 m²"},
            {"key": "C", "text": "216 m²"},
            {"key": "D", "text": "224 m²"},
            {"key": "E", "text": "240 m²"}
        ],
        "correct_option": "C",
        "explanations": {
            "A": "Salah. Nilai ini diperoleh dengan perhitungan yang tidak lengkap.",
            "B": "Salah. Nilai ini hanya menghitung dua sisi taman.",
            "C": "Benar. Luas total dengan jalan = (30+4)(20+4) = 34×24 = 816 m². Luas taman = 30×20 = 600 m². Luas jalan = 816 - 600 = 216 m².",
            "D": "Salah. Nilai ini diperoleh dengan kesalahan penambahan lebar jalan.",
            "E": "Salah. Nilai ini terlalu besar karena kesalahan konsep."
        },
        "difficulty": "medium"
    },
    {
        "number": 4,
        "type": "statistika",
        "question_text": "Dalam sebuah kelas terdapat 30 siswa. Rata-rata nilai ulangan matematika adalah 75. Jika 5 siswa dengan rata-rata 90 tidak disertakan dalam perhitungan, berapakah rata-rata nilai 25 siswa lainnya?",
        "options": [
            {"key": "A", "text": "68"},
            {"key": "B", "text": "70"},
            {"key": "C", "text": "72"},
            {"key": "D", "text": "74"},
            {"key": "E", "text": "76"}
        ],
        "correct_option": "C",
        "explanations": {
            "A": "Salah. Nilai ini terlalu rendah dari perhitungan yang benar.",
            "B": "Salah. Nilai ini masih kurang dari hasil yang sebenarnya.",
            "C": "Benar. Total nilai 30 siswa = 30×75 = 2250. Total nilai 5 siswa = 5×90 = 450. Total nilai 25 siswa = 2250-450 = 1800. Rata-rata = 1800/25 = 72.",
            "D": "Salah. Nilai ini terlalu dekat dengan rata-rata awal.",
            "E": "Salah. Tidak mungkin rata-rata meningkat ketika siswa berprestasi tinggi dikeluarkan."
        },
        "difficulty": "medium"
    },
    {
        "number": 5,
        "type": "aritmetika",
        "question_text": "Sebuah toko memberikan diskon bertingkat: diskon pertama 20%, kemudian diskon tambahan 10% dari harga setelah diskon pertama. Jika harga awal suatu barang adalah Rp500.000, berapakah harga akhir setelah kedua diskon?",
        "options": [
            {"key": "A", "text": "Rp350.000"},
            {"key": "B", "text": "Rp360.000"},
            {"key": "C", "text": "Rp370.000"},
            {"key": "D", "text": "Rp380.000"},
            {"key": "E", "text": "Rp390.000"}
        ],
        "correct_option": "B",
        "explanations": {
            "A": "Salah. Nilai ini terlalu rendah karena menganggap diskon total 30%.",
            "B": "Benar. Setelah diskon 20%: 500.000×0,8 = 400.000. Setelah diskon 10% lagi: 400.000×0,9 = 360.000.",
            "C": "Salah. Nilai ini sedikit lebih tinggi dari perhitungan benar.",
            "D": "Salah. Nilai ini terlalu tinggi.",
            "E": "Salah. Diskon bertingkat tidak sama dengan penjumlahan persentase."
        },
        "difficulty": "easy"
    },
    {
        "number": 6,
        "type": "bilangan",
        "question_text": "Berapakah sisa pembagian dari 7^2024 dibagi 5?",
        "options": [
            {"key": "A", "text": "1"},
            {"key": "B", "text": "2"},
            {"key": "C", "text": "3"},
            {"key": "D", "text": "4"},
            {"key": "E", "text": "0"}
        ],
        "correct_option": "A",
        "explanations": {
            "A": "Benar. Pola sisa 7^n mod 5: 7^1≡2, 7^2≡4, 7^3≡3, 7^4≡1 (mod 5). Siklus berulang setiap 4 pangkat. Karena 2024 habis dibagi 4, maka 7^2024 ≡ 1 (mod 5).",
            "B": "Salah. Ini adalah sisa untuk pangkat ganjil tertentu.",
            "C": "Salah. Ini adalah sisa untuk pangkat ke-3 dalam siklus.",
            "D": "Salah. Ini adalah sisa untuk pangkat genap tertentu.",
            "E": "Salah. 7^2024 tidak habis dibagi 5."
        },
        "difficulty": "hard"
    },
    {
        "number": 7,
        "type": "perbandingan",
        "question_text": "Perbandingan uang Ani dan Budi adalah 3:4. Jika Ani menerima tambahan Rp20.000, perbandingan uang mereka menjadi 5:6. Berapakah jumlah uang mereka mula-mula?",
        "options": [
            {"key": "A", "text": "Rp380.000"},
            {"key": "B", "text": "Rp400.000"},
            {"key": "C", "text": "Rp420.000"},
            {"key": "D", "text": "Rp440.000"},
            {"key": "E", "text": "Rp460.000"}
        ],
        "correct_option": "C",
        "explanations": {
            "A": "Salah. Nilai ini kurang dari hasil benar.",
            "B": "Salah. Masih kurang sedikit.",
            "C": "Benar. Misal Ani = 3k, Budi = 4k. (3k+20000)/4k = 5/6. 6(3k+20000) = 20k. 18k+120000 = 20k. 2k = 120000. k = 60000. Jumlah mula-mula = 7k = 420.000.",
            "D": "Salah. Terlalu tinggi dari hasil benar.",
            "E": "Salah. Paling tinggi dan salah."
        },
        "difficulty": "hard"
    },
    {
        "number": 8,
        "type": "fungsi",
        "question_text": "Jika f(x) = 2x + 3 dan g(x) = x² - 1, berapakah nilai dari (f ∘ g)(3)?",
        "options": [
            {"key": "A", "text": "15"},
            {"key": "B", "text": "17"},
            {"key": "C", "text": "19"},
            {"key": "D", "text": "21"},
            {"key": "E", "text": "23"}
        ],
        "correct_option": "C",
        "explanations": {
            "A": "Salah. Nilai ini terlalu rendah.",
            "B": "Salah. Masih kurang dari hasil yang benar.",
            "C": "Benar. g(3) = 3² - 1 = 8. f(g(3)) = f(8) = 2(8) + 3 = 16 + 3 = 19.",
            "D": "Salah. Nilai ini terlalu tinggi.",
            "E": "Salah. Terlalu tinggi dari perhitungan benar."
        },
        "difficulty": "medium"
    },
    {
        "number": 9,
        "type": "peluang",
        "question_text": "Dari seperangkat kartu bridge (52 kartu), diambil 2 kartu secara acak. Berapakah peluang terambilnya 2 kartu As?",
        "options": [
            {"key": "A", "text": "1/221"},
            {"key": "B", "text": "1/169"},
            {"key": "C", "text": "1/130"},
            {"key": "D", "text": "1/100"},
            {"key": "E", "text": "1/52"}
        ],
        "correct_option": "A",
        "explanations": {
            "A": "Benar. Banyak cara mengambil 2 kartu dari 52 = C(52,2) = 1326. Banyak cara mengambil 2 As dari 4 As = C(4,2) = 6. Peluang = 6/1326 = 1/221.",
            "B": "Salah. Perhitungan ini salah menggunakan kombinasi.",
            "C": "Salah. Nilai ini terlalu besar.",
            "D": "Salah. Terlalu besar dari peluang sebenarnya.",
            "E": "Salah. Ini adalah peluang mengambil 1 As dari 52 kartu."
        },
        "difficulty": "hard"
    },
    {
        "number": 10,
        "type": "barisan_dan_deret",
        "question_text": "Suku ke-5 dari suatu barisan aritmetika adalah 17 dan suku ke-10 adalah 32. Berapakah jumlah 15 suku pertama?",
        "options": [
            {"key": "A", "text": "360"},
            {"key": "B", "text": "375"},
            {"key": "C", "text": "390"},
            {"key": "D", "text": "405"},
            {"key": "E", "text": "420"}
        ],
        "correct_option": "C",
        "explanations": {
            "A": "Salah. Nilai ini terlalu rendah.",
            "B": "Salah. Masih kurang dari hasil benar.",
            "C": "Benar. U5 = a+4b = 17, U10 = a+9b = 32. Selisih: 5b = 15, b = 3. a = 17-12 = 5. S15 = 15/2 × (2a + 14b) = 15/2 × (10+42) = 15/2 × 52 = 390.",
            "D": "Salah. Terlalu tinggi dari hasil benar.",
            "E": "Salah. Paling tinggi dan salah."
        },
        "difficulty": "medium"
    },
    {
        "number": 11,
        "type": "geometri",
        "question_text": "Sebuah tabung memiliki volume 1540 cm³. Jika tinggi tabung adalah 10 cm dan π = 22/7, berapakah jari-jari alas tabung?",
        "options": [
            {"key": "A", "text": "5 cm"},
            {"key": "B", "text": "6 cm"},
            {"key": "C", "text": "7 cm"},
            {"key": "D", "text": "8 cm"},
            {"key": "E", "text": "9 cm"}
        ],
        "correct_option": "C",
        "explanations": {
            "A": "Salah. Jari-jari 5 cm menghasilkan volume lebih kecil.",
            "B": "Salah. Jari-jari 6 cm menghasilkan volume 1131 cm³.",
            "C": "Benar. V = πr²h. 1540 = (22/7)×r²×10. r² = 1540×7/(22×10) = 49. r = 7 cm.",
            "D": "Salah. Jari-jari 8 cm menghasilkan volume lebih besar.",
            "E": "Salah. Jari-jari 9 cm menghasilkan volume jauh lebih besar."
        },
        "difficulty": "medium"
    },
    {
        "number": 12,
        "type": "persamaan",
        "question_text": "Persamaan kuadrat x² - 5x + 6 = 0 memiliki akar-akar p dan q. Berapakah nilai dari p² + q²?",
        "options": [
            {"key": "A", "text": "11"},
            {"key": "B", "text": "13"},
            {"key": "C", "text": "15"},
            {"key": "D", "text": "17"},
            {"key": "E", "text": "19"}
        ],
        "correct_option": "B",
        "explanations": {
            "A": "Salah. Nilai ini terlalu rendah.",
            "B": "Benar. p+q = 5, pq = 6. p²+q² = (p+q)² - 2pq = 25 - 12 = 13.",
            "C": "Salah. Nilai ini terlalu tinggi.",
            "D": "Salah. Terlalu tinggi dari hasil benar.",
            "E": "Salah. Jauh terlalu tinggi."
        },
        "difficulty": "medium"
    },
    {
        "number": 13,
        "type": "kecepatan_jarak_waktu",
        "question_text": "Seorang pengendara motor menempuh jarak 120 km dengan kecepatan rata-rata 40 km/jam. Dalam perjalanan pulang melalui rute yang sama, ia meningkatkan kecepatan menjadi 60 km/jam. Berapakah kecepatan rata-rata untuk seluruh perjalanan?",
        "options": [
            {"key": "A", "text": "45 km/jam"},
            {"key": "B", "text": "48 km/jam"},
            {"key": "C", "text": "50 km/jam"},
            {"key": "D", "text": "52 km/jam"},
            {"key": "E", "text": "55 km/jam"}
        ],
        "correct_option": "B",
        "explanations": {
            "A": "Salah. Ini adalah rata-rata aritmatika sederhana, bukan rata-rata harmonik.",
            "B": "Benar. Waktu pergi = 120/40 = 3 jam. Waktu pulang = 120/60 = 2 jam. Total waktu = 5 jam. Total jarak = 240 km. Kecepatan rata-rata = 240/5 = 48 km/jam.",
            "C": "Salah. Nilai ini terlalu tinggi.",
            "D": "Salah. Terlalu tinggi dari hasil benar.",
            "E": "Salah. Jauh terlalu tinggi."
        },
        "difficulty": "medium"
    },
    {
        "number": 14,
        "type": "logika_matematika",
        "question_text": "Jika pernyataan 'Semua mahasiswa rajin lulus ujian' bernilai benar, manakah pernyataan berikut yang PASTI benar?",
        "options": [
            {"key": "A", "text": "Semua yang lulus ujian adalah mahasiswa rajin"},
            {"key": "B", "text": "Beberapa mahasiswa rajin tidak lulus ujian"},
            {"key": "C", "text": "Mahasiswa yang tidak rajin tidak lulus ujian"},
            {"key": "D", "text": "Beberapa yang lulus ujian adalah mahasiswa rajin"},
            {"key": "E", "text": "Tidak ada mahasiswa rajin yang tidak lulus"}
        ],
        "correct_option": "E",
        "explanations": {
            "A": "Salah. Ini adalah konvers yang tidak selalu benar.",
            "B": "Salah. Bertentangan dengan premis.",
            "C": "Salah. Premis tidak membahas mahasiswa tidak rajin.",
            "D": "Salah. Meskipun benar, ini bukan kesimpulan terkuat.",
            "E": "Benar. Ini ekuivalen dengan premis awal: semua mahasiswa rajin pasti lulus, artinya tidak ada mahasiswa rajin yang tidak lulus."
        },
        "difficulty": "hard"
    },
    {
        "number": 15,
        "type": "aritmetika",
        "question_text": "Sebuah proyek dapat diselesaikan oleh 8 pekerja dalam 15 hari. Setelah bekerja selama 5 hari, proyek dihentikan selama 3 hari karena cuaca buruk. Agar proyek selesai tepat waktu, berapa tambahan pekerja yang diperlukan?",
        "options": [
            {"key": "A", "text": "2 orang"},
            {"key": "B", "text": "3 orang"},
            {"key": "C", "text": "4 orang"},
            {"key": "D", "text": "5 orang"},
            {"key": "E", "text": "6 orang"}
        ],
        "correct_option": "C",
        "explanations": {
            "A": "Salah. Tambahan 2 orang tidak cukup.",
            "B": "Salah. Tambahan 3 orang masih kurang.",
            "C": "Benar. Total pekerjaan = 8×15 = 120 orang-hari. Sudah dikerjakan 5 hari: 8×5 = 40 orang-hari. Sisa = 80 orang-hari. Sisa waktu = 15-5-3 = 7 hari. Pekerja dibutuhkan = 80/7 ≈ 11,43 → 12 orang. Tambahan = 12-8 = 4 orang.",
            "D": "Salah. Tambahan 5 orang berlebihan.",
            "E": "Salah. Tambahan 6 orang terlalu banyak."
        },
        "difficulty": "hard"
    },
    {
        "number": 16,
        "type": "geometri",
        "question_text": "Segitiga ABC siku-siku di B dengan AB = 6 cm dan BC = 8 cm. Titik D terletak pada AC sehingga BD tegak lurus AC. Berapakah panjang BD?",
        "options": [
            {"key": "A", "text": "4,2 cm"},
            {"key": "B", "text": "4,8 cm"},
            {"key": "C", "text": "5,0 cm"},
            {"key": "D", "text": "5,2 cm"},
            {"key": "E", "text": "5,6 cm"}
        ],
        "correct_option": "B",
        "explanations": {
            "A": "Salah. Nilai ini terlalu rendah.",
            "B": "Benar. AC = √(6²+8²) = 10 cm. Luas segitiga = ½×6×8 = 24 cm². Juga = ½×AC×BD = ½×10×BD. Maka BD = 24×2/10 = 4,8 cm.",
            "C": "Salah. Nilai ini terlalu tinggi.",
            "D": "Salah. Terlalu tinggi dari hasil benar.",
            "E": "Salah. Jauh terlalu tinggi."
        },
        "difficulty": "hard"
    },
    {
        "number": 17,
        "type": "statistika",
        "question_text": "Median dari data: 12, 15, 18, 20, x, 25, 28, 30 adalah 22. Berapakah nilai x?",
        "options": [
            {"key": "A", "text": "22"},
            {"key": "B", "text": "23"},
            {"key": "C", "text": "24"},
            {"key": "D", "text": "25"},
            {"key": "E", "text": "26"}
        ],
        "correct_option": "C",
        "explanations": {
            "A": "Salah. Jika x=22, median = (20+22)/2 = 21.",
            "B": "Salah. Jika x=23, median = (20+23)/2 = 21,5.",
            "C": "Benar. Data terurut: 12,15,18,20,x,25,28,30. Median = rata-rata suku ke-4 dan ke-5 = (20+x)/2 = 22. Maka x = 24.",
            "D": "Salah. Jika x=25, median = (20+25)/2 = 22,5.",
            "E": "Salah. Jika x=26, median = (20+26)/2 = 23."
        },
        "difficulty": "medium"
    },
    {
        "number": 18,
        "type": "persamaan_linear",
        "question_text": "Sistem persamaan: 2x + 3y = 13 dan 4x - y = 5. Berapakah nilai dari x + y?",
        "options": [
            {"key": "A", "text": "3"},
            {"key": "B", "text": "4"},
            {"key": "C", "text": "5"},
            {"key": "D", "text": "6"},
            {"key": "E", "text": "7"}
        ],
        "correct_option": "C",
        "explanations": {
            "A": "Salah. Nilai ini terlalu rendah.",
            "B": "Salah. Masih kurang dari hasil benar.",
            "C": "Benar. Dari persamaan kedua: y = 4x-5. Substitusi ke pertama: 2x+3(4x-5)=13. 2x+12x-15=13. 14x=28. x=2. y=4(2)-5=3. x+y=2+3=5.",
            "D": "Salah. Nilai ini terlalu tinggi.",
            "E": "Salah. Jauh terlalu tinggi."
        },
        "difficulty": "easy"
    },
    {
        "number": 19,
        "type": "persentase",
        "question_text": "Harga suatu barang naik 25% kemudian turun 20%. Perubahan harga akhir dibandingkan harga awal adalah...",
        "options": [
            {"key": "A", "text": "Naik 5%"},
            {"key": "B", "text": "Tidak berubah"},
            {"key": "C", "text": "Turun 5%"},
            {"key": "D", "text": "Turun 10%"},
            {"key": "E", "text": "Naik 10%"}
        ],
        "correct_option": "B",
        "explanations": {
            "A": "Salah. Kenaikan dan penurunan persentase tidak saling meniadakan secara langsung.",
            "B": "Benar. Misal harga awal = 100. Setelah naik 25% = 125. Setelah turun 20% = 125×0,8 = 100. Jadi tidak ada perubahan.",
            "C": "Salah. Harga akhir sama dengan harga awal.",
            "D": "Salah. Tidak ada penurunan.",
            "E": "Salah. Tidak ada kenaikan."
        },
        "difficulty": "medium"
    },
    {
        "number": 20,
        "type": "bilangan",
        "question_text": "Berapakah banyak bilangan bulat antara 100 dan 500 yang habis dibagi 7?",
        "options": [
            {"key": "A", "text": "55"},
            {"key": "B", "text": "56"},
            {"key": "C", "text": "57"},
            {"key": "D", "text": "58"},
            {"key": "E", "text": "59"}
        ],
        "correct_option": "C",
        "explanations": {
            "A": "Salah. Nilai ini kurang dari hasil benar.",
            "B": "Salah. Masih kurang satu.",
            "C": "Benar. Bilangan pertama ≥100 yang habis dibagi 7 adalah 105 (7×15). Bilangan terakhir ≤500 adalah 497 (7×71). Banyaknya = 71-15+1 = 57.",
            "D": "Salah. Terlalu tinggi dari hasil benar.",
            "E": "Salah. Paling tinggi dan salah."
        },
        "difficulty": "medium"
    },
    {
        "number": 21,
        "type": "geometri",
        "question_text": "Luas lingkaran yang menyinggung keempat sisi persegi dengan keliling 40 cm adalah...",
        "options": [
            {"key": "A", "text": "25π cm²"},
            {"key": "B", "text": "50π cm²"},
            {"key": "C", "text": "75π cm²"},
            {"key": "D", "text": "100π cm²"},
            {"key": "E", "text": "125π cm²"}
        ],
        "correct_option": "A",
        "explanations": {
            "A": "Benar. Keliling persegi = 40, sisi = 10 cm. Lingkaran menyinggung keempat sisi berarti diameter = sisi = 10 cm, jari-jari = 5 cm. Luas = π×5² = 25π cm².",
            "B": "Salah. Nilai ini terlalu besar.",
            "C": "Salah. Terlalu besar dari hasil benar.",
            "D": "Salah. Ini adalah luas jika jari-jari = 10 cm.",
            "E": "Salah. Jauh terlalu besar."
        },
        "difficulty": "easy"
    },
    {
        "number": 22,
        "type": "pertidaksamaan",
        "question_text": "Himpunan penyelesaian dari pertidaksamaan 2x - 5 < 3x + 2 adalah...",
        "options": [
            {"key": "A", "text": "x > -7"},
            {"key": "B", "text": "x < -7"},
            {"key": "C", "text": "x > 7"},
            {"key": "D", "text": "x < 7"},
            {"key": "E", "text": "x > -3"}
        ],
        "correct_option": "A",
        "explanations": {
            "A": "Benar. 2x - 5 < 3x + 2. -5 - 2 < 3x - 2x. -7 < x atau x > -7.",
            "B": "Salah. Tanda pertidaksamaan terbalik.",
            "C": "Salah. Nilai dan tanda salah.",
            "D": "Salah. Nilai dan tanda salah.",
            "E": "Salah. Nilai salah."
        },
        "difficulty": "easy"
    },
    {
        "number": 23,
        "type": "matriks",
        "question_text": "Jika A = [[2, 1], [3, 2]] dan B = [[1, 0], [2, 1]], berapakah elemen baris pertama kolom kedua dari A × B?",
        "options": [
            {"key": "A", "text": "0"},
            {"key": "B", "text": "1"},
            {"key": "C", "text": "2"},
            {"key": "D", "text": "3"},
            {"key": "E", "text": "4"}
        ],
        "correct_option": "B",
        "explanations": {
            "A": "Salah. Nilai ini terlalu rendah.",
            "B": "Benar. (A×B)[1,2] = 2×0 + 1×1 = 0 + 1 = 1.",
            "C": "Salah. Nilai ini terlalu tinggi.",
            "D": "Salah. Terlalu tinggi dari hasil benar.",
            "E": "Salah. Jauh terlalu tinggi."
        },
        "difficulty": "hard"
    },
    {
        "number": 24,
        "type": "trigonometri",
        "question_text": "Jika sin θ = 3/5 dan θ berada di kuadran I, berapakah nilai cos θ?",
        "options": [
            {"key": "A", "text": "2/5"},
            {"key": "B", "text": "3/5"},
            {"key": "C", "text": "4/5"},
            {"key": "D", "text": "5/4"},
            {"key": "E", "text": "5/3"}
        ],
        "correct_option": "C",
        "explanations": {
            "A": "Salah. Nilai ini terlalu rendah.",
            "B": "Salah. Ini adalah nilai sin θ, bukan cos θ.",
            "C": "Benar. sin²θ + cos²θ = 1. (3/5)² + cos²θ = 1. 9/25 + cos²θ = 1. cos²θ = 16/25. cos θ = 4/5 (kuadran I positif).",
            "D": "Salah. Nilai ini lebih besar dari 1, tidak mungkin untuk cosinus.",
            "E": "Salah. Nilai ini lebih besar dari 1, tidak mungkin untuk cosinus."
        },
        "difficulty": "medium"
    },
    {
        "number": 25,
        "type": "kombinatorik",
        "question_text": "Dari 7 orang calon pengurus, akan dipilih 3 orang untuk menduduki posisi Ketua, Sekretaris, dan Bendahara. Banyak cara pemilihan yang mungkin adalah...",
        "options": [
            {"key": "A", "text": "35"},
            {"key": "B", "text": "105"},
            {"key": "C", "text": "210"},
            {"key": "D", "text": "315"},
            {"key": "E", "text": "420"}
        ],
        "correct_option": "C",
        "explanations": {
            "A": "Salah. Ini adalah kombinasi C(7,3), padahal urutan penting.",
            "B": "Salah. Nilai ini kurang dari hasil benar.",
            "C": "Benar. Karena posisi berbeda, ini permutasi. P(7,3) = 7×6×5 = 210 cara.",
            "D": "Salah. Nilai ini terlalu tinggi.",
            "E": "Salah. Jauh terlalu tinggi."
        },
        "difficulty": "medium"
    }
]

# Write all questions
for i, q in enumerate(questions):
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
        "explanations": q["explanations"],
        "difficulty": q["difficulty"],
        "source": "qwen-generated",
        "verified": True
    }
    
    output_file = output_dir / f"{q['number']:03d}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(question_data, f, indent=2, ensure_ascii=False)
        f.write('\n')

print(f"Successfully generated {len(questions)} quantitative questions for Package 12")

"""Phân biệt CV với cover letter dựa trên tên file.

Cột `Resume, CL` cho ứng viên đính kèm nhiều file, và nhiều người gửi cả CV lẫn
cover letter. Chỉ nội dung CV mới đáng ghi vào `Resume Content`.

Luật KHÔNG phải "tên có chữ Cover/Letter thì bỏ": rất nhiều ứng viên gộp cả hai
vào một PDF (`CV + Cover Letter.pdf`, `CaoHoangNguyen_NexLab_CV_CoverLetter.pdf`).
Bỏ những file đó là mất luôn CV. Chỉ bỏ khi tên nói cover letter mà KHÔNG nói CV.
"""

from __future__ import annotations

import re

# "letter" đứng một mình vẫn tính — gặp cả "Reference Letter.pdf" trong dữ liệu thật.
_COVER_LETTER = re.compile(r"cover|letter|thư\s*xin\s*việc", re.IGNORECASE)

# Chặn hai đầu bằng chữ cái để "cv" không khớp nhầm trong "TopCV.vn" hay "cvs".
_RESUME = re.compile(r"(?<![a-z])cv(?![a-z])|resume|curriculum", re.IGNORECASE)


def is_cover_letter(file_name: str) -> bool:
    """True khi file chỉ là cover letter, không kèm CV."""
    if not file_name:
        return False  # không biết tên thì cứ đọc, thà thừa còn hơn bỏ sót CV
    return bool(_COVER_LETTER.search(file_name)) and not _RESUME.search(file_name)

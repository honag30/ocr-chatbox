import re

def group_results_by_line(raw_results, y_tolerance=20):
    """
    Gom nhóm các cụm chữ nằm trên CÙNG MỘT DÒNG NGANG (tọa độ Y tương đương).
    Tự động thích ứng theo chiều cao chữ (adaptive vertical tolerance) để tránh
    tách 1 dòng thành nhiều dòng riêng lẻ trên ảnh có độ phân giải lớn hoặc chữ to.
    Trả về tuple: (formatted_lines, line_confidences)
    """
    boxes = []
    for item in raw_results:
        bbox, text, prob = item[0], item[1], item[2]
        if prob < 0.15:
            continue
        ys = [p[1] for p in bbox]
        xs = [p[0] for p in bbox]
        y_min, y_max = min(ys), max(ys)
        height = max(1.0, y_max - y_min)
        y_center = sum(ys) / len(ys)
        x_min = min(xs)
        boxes.append({
            'bbox': bbox,
            'text': text,
            'prob': prob,
            'y_center': y_center,
            'y_min': y_min,
            'y_max': y_max,
            'height': height,
            'x_min': x_min
        })

    # Sắp xếp theo Y_center từ trên xuống dưới
    boxes.sort(key=lambda b: b['y_center'])

    lines = []
    for box in boxes:
        if not lines:
            lines.append([box])
        else:
            placed = False
            for line in lines:
                line_y_mean = sum(b['y_center'] for b in line) / len(line)
                line_avg_h = sum(b['height'] for b in line) / len(line)
                adaptive_tol = max(y_tolerance, line_avg_h * 0.45)
                if abs(box['y_center'] - line_y_mean) <= adaptive_tol:
                    line.append(box)
                    placed = True
                    break
            if not placed:
                lines.append([box])

    formatted_lines = []
    line_confidences = []

    for line in lines:
        line.sort(key=lambda b: b['x_min'])  # Xếp từ trái sang phải
        line_text = " ".join([b['text'] for b in line])

        # Chuẩn hóa khoảng cách và dấu gạch nối giữa Thời gian (hh:mm - dd/mm/yyyy)
        line_text = re.sub(r'(\d{2}:\d{2})\s*[\~2\=]\s*(\d{2}/\d{2}/\d{4})', r'\1 - \2', line_text)

        # Tính độ tin cậy trung bình của dòng
        avg_prob = sum([b['prob'] for b in line]) / len(line) if line else 0.0

        formatted_lines.append(line_text)
        line_confidences.append(avg_prob)

    return formatted_lines, line_confidences

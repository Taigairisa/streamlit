def count_rows(sheet):
    values = sheet.get_all_values()
    return len(values)

def count_columns(sheet):
    values = sheet.get_all_values()
    if not values:
        return 0  # シートにデータがない場合、0を返す

    # 各行の列数を調べて最大の列数を取得
    max_column_count = max(len(row) for row in values)
    return max_column_count

def copyDataToBudgetSheet(questions, sheet, lastRow = False):
    if lastRow:
        targetRow = count_rows(sheet)  # 家計簿シートに追加する行
        for num, question in enumerate(questions):
            question_category, answer = question[0], question[1]
            sheet.update_cell(targetRow + 1, num+1, answer)
    else:
        targetRow = 0
        for num, question in enumerate(questions):
            question_category = question[0]
            sheet.update_cell(targetRow + 1, num+1, question_category)
    # フォームからのデータをリストとして受け取る
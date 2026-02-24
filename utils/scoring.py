def calculate_scholarship(percentage):
    if percentage >= 100:
        return 95, 'Great scholarship opportunity for a brilliant mind - Congratulations!'
    if percentage >= 90:
        return 70, 'What a score - Well Done!'
    if percentage >= 75:
        return 50, 'Good effort!'
    if percentage >= 50:
        return 25, 'Quarter Scholarship - Keep Trying!'
    return 10, "A scholarship for participation - Don't give up, keep learning!"


def get_test_duration_minutes(class_level):
    duration_map = {
        'class9': 30,
        'class10': 30,
        'class11': 40,
        'class12': 45,
        'dropper': 45,
    }
    return duration_map.get(class_level, 60)

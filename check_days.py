from datetime import datetime
dias = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"]
print("Dias de julio 2026:")
for dia in [15, 16, 17, 20, 21, 22, 23, 24, 27, 30]:
    d = datetime(2026, 7, dia)
    print(f"  {dia}: {dias[d.weekday()]}")

import csv
from datetime import datetime, timedelta

print("🚀 Generando eventos masivos para temporada 2026...")

# Configuración
start_date = datetime(2026, 5, 1)
end_date = datetime(2026, 10, 1)

# Mapeo de eventos por discoteca y día de semana
eventos_por_discoteca = {
    'ushuaia': {
        0: [('F*** ME I\'M FAMOUS!', 'David Guetta & Friends', 65, 150)],  # Lunes
        1: [('Calvin Harris', 'Calvin Harris', 80, 200)],  # Martes
        2: [('Tomorrowland', 'Dimitri Vegas & Like Mike', 70, 160)],  # Miércoles
        3: [('Martin Garrix', 'Martin Garrix', 70, 160)],  # Jueves
        4: [('Calvin Harris', 'Calvin Harris', 80, 200)],  # Viernes
        5: [('ANTS', 'Lineup estelar', 65, 150)],  # Sábado
        6: [('Swedish House Mafia', 'SHM', 75, 180)]  # Domingo
    },
    'hi-ibiza': {
        0: [('Solèy', 'Francis Mercier & Guests', 60, 140)],
        1: [('eastenderz', 'East End Dubs & Guests', 55, 130)],
        2: [('OUR HOUSE', 'MEDUZA + James Hype', 65, 150)],
        3: [('bed', 'Lineup TBA', 50, 120)],
        4: [('Dom Dolla', 'Dom Dolla & Friends', 60, 140)],
        5: [('Black Coffee', 'Black Coffee & Friends', 65, 150)],
        6: [('The Anarchist', 'Lineup TBA', 55, 130)]
    },
    'pacha': {
        0: [('Sonny Fodera', 'Sonny Fodera & Friends', 45, 120)],
        1: [('Vintage Culture', 'Vintage Culture', 50, 120)],
        2: [('Abracadabra', 'BLOND:ISH & Friends', 50, 120)],
        3: [('Music On', 'Marco Carola', 55, 130)],
        4: [('Music On', 'Marco Carola', 55, 130)],
        5: [('Robin Schulz', 'Robin Schulz & Friends', 50, 120)],
        6: [('Solomun +1', 'Solomun', 60, 140)]
    },
    'unvrs': {
        0: [('Experts Only', 'John Summit', 70, 180)],
        1: [('ÆDEN', 'Anyma', 80, 200)],
        2: [('Paradise', 'Jamie Jones', 65, 170)],
        3: [('FISHER', 'FISHER & Friends', 70, 180)],
        4: [('Galactic Circus', 'David Guetta', 75, 190)],
        5: [('elrow', 'Enter the Wortex', 70, 180)],
        6: [('Carl Cox', 'Carl Cox all-night-long', 75, 190)]
    },
    'amnesia': {
        1: [('Cocoon', 'Sven Väth', 55, 130)],  # Martes
        4: [('Glitterbox', 'Armand Van Helden', 60, 140)],  # Viernes
        5: [('elrow', 'Lineup loco', 55, 130)],  # Sábado
        6: [('Together', 'Lineup TBA', 50, 120)]  # Domingo
    },
    'dc10': {
        0: [('Circoloco', 'Lineup TBA', 50, 130)],  # Lunes
        5: [('Circoloco', 'Lineup TBA', 55, 140)]   # Sábado
    },
    'eden': {
        3: [('Toolroom', 'Lineup TBA', 35, 80)],  # Jueves
        4: [('Viva Warriors', 'Lineup TBA', 35, 80)],  # Viernes
        5: [('Defected', 'Lineup TBA', 40, 90)]  # Sábado
    }
}

# Generar eventos
eventos = []
current_date = start_date
total_eventos = 0

print("📅 Generando eventos desde mayo a octubre 2026...")

while current_date <= end_date:
    dia_semana = current_date.weekday()
    
    for discoteca, eventos_dia in eventos_por_discoteca.items():
        if dia_semana in eventos_dia:
            for evento_info in eventos_dia[dia_semana]:
                nombre, subtitulo, precio_min, precio_max = evento_info
                fecha_str = current_date.strftime("%Y%m%d")
                nombre_limpio = nombre.replace("'", "").replace("&", "and").replace("!", "")
                slug = f'{discoteca}-{fecha_str}-{nombre_limpio[:20].lower().replace(" ", "-")}'
                
                # Fechas (asumimos que empieza a las 23:59)
                start = current_date.replace(hour=23, minute=59).isoformat() + 'Z'
                end = (current_date + timedelta(days=1)).replace(hour=6, minute=0).isoformat() + 'Z'
                door = current_date.replace(hour=23, minute=0).isoformat() + 'Z'
                
                titulo = f'{nombre} @ {current_date.strftime("%d %b %Y")}'
                
                eventos.append([
                    slug,
                    titulo,
                    discoteca,
                    subtitulo,
                    f'{nombre} en {discoteca} - {current_date.strftime("%d/%m/%Y")}',
                    'event',
                    start,
                    end,
                    door,
                    'EUR',
                    str(precio_min),
                    str(precio_max),
                    f'https://{discoteca}.com/tickets',
                    f'https://images.ibizaglam.app/{discoteca}-event.jpg',
                    'scheduled',
                    'true',
                    'manual',
                    '{}'
                ])
                total_eventos += 1
    
    # Mostrar progreso cada 30 días
    if current_date.day == 1:
        print(f"  ✓ Procesado {current_date.strftime('%B %Y')}")
    
    current_date += timedelta(days=1)

# Guardar a CSV
with open('input/eventos_completo.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['slug','title','discoteca_slug','subtitle','description','event_type',
                    'start_at','end_at','door_open_at','currency','price_from','price_to',
                    'tickets_url','poster_url','status','active','source','metadata'])
    writer.writerows(eventos)

print(f"\n✅ ¡COMPLETADO! Generados {total_eventos} eventos para la temporada 2026")
print(f"📁 Archivo guardado en: input/eventos_completo.csv")

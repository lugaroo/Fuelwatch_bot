"""
Генерация отчётов администратора (HTML). Минимальная версия — только ID.
Путь: Fuelwatch_bot/services/admin_stats.py
"""

import sqlite3
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import Counter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = str(PROJECT_ROOT / "stations.db")
REPORTS_DIR = PROJECT_ROOT / "reports"


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_full_stats() -> dict:
    """Полная статистика для админ-панели."""
    conn = _connect()
    cur = conn.cursor()

    # Пользователи (только ID)
    cur.execute("SELECT COUNT(*) FROM user_ids")
    total_users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM user_ids WHERE last_seen > datetime('now', '-1 day')")
    active_24h = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM user_ids WHERE last_seen > datetime('now', '-7 days')")
    active_7d = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM user_ids WHERE last_seen > datetime('now', '-30 days')")
    active_30d = cur.fetchone()[0]

    # Активность
    cur.execute("SELECT COUNT(*) FROM activity_log WHERE activity_type = 'update'")
    total_updates = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM activity_log WHERE activity_type = 'search'")
    total_searches = cur.fetchone()[0]

    # Станции
    cur.execute("SELECT COUNT(*) FROM stations WHERE active = 1")
    active_stations = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM stations")
    total_stations = cur.fetchone()[0]

    # Топ-10 обновляторов (только ID, без имён)
    cur.execute("""
        SELECT user_id, COUNT(*) as cnt
        FROM activity_log
        WHERE activity_type = 'update'
        GROUP BY user_id
        ORDER BY cnt DESC
        LIMIT 10
    """)
    top_updaters = [dict(row) for row in cur.fetchall()]

    # Статистика по топливу
    cur.execute("""
        SELECT fuel_type, status, COUNT(*) as cnt
        FROM fuel_status
        GROUP BY fuel_type, status
        ORDER BY cnt DESC
    """)
    fuel_stats_raw = [dict(row) for row in cur.fetchall()]

    # Последние синхронизации
    cur.execute("""
        SELECT * FROM sync_log
        ORDER BY started_at DESC
        LIMIT 5
    """)
    recent_syncs = [dict(row) for row in cur.fetchall()]

    conn.close()

    return {
        "total_users": total_users,
        "active_24h": active_24h,
        "active_7d": active_7d,
        "active_30d": active_30d,
        "total_updates": total_updates,
        "total_searches": total_searches,
        "active_stations": active_stations,
        "total_stations": total_stations,
        "top_updaters": top_updaters,
        "fuel_stats": fuel_stats_raw,
        "recent_syncs": recent_syncs,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }


def generate_html() -> Path:
    """Генерирует красивый HTML-отчёт. Возвращает путь к файлу."""
    REPORTS_DIR.mkdir(exist_ok=True)
    stats = get_full_stats()

    # Подготовка данных для графиков
    fuel_by_type = Counter()
    fuel_by_status = Counter()
    for row in stats["fuel_stats"]:
        fuel_by_type[row["fuel_type"]] += row["cnt"]
        fuel_by_status[row["status"]] += row["cnt"]

    fuel_type_labels = json.dumps(list(fuel_by_type.keys()))
    fuel_type_values = json.dumps(list(fuel_by_type.values()))
    fuel_status_labels = json.dumps(list(fuel_by_status.keys()))
    fuel_status_values = json.dumps(list(fuel_by_status.values()))

    top_updaters_rows = ""
    for i, u in enumerate(stats["top_updaters"], 1):
        top_updaters_rows += f"""
            <tr>
                <td>{i}</td>
                <td><code>{u['user_id']}</code></td>
                <td>{u['cnt']}</td>
            </tr>
        """

    recent_syncs_rows = ""
    for s in stats["recent_syncs"]:
        status_icon = "✅" if s["status"] == "success" else "❌"
        recent_syncs_rows += f"""
            <tr>
                <td>{status_icon}</td>
                <td>#{s['id']}</td>
                <td>{s['started_at']}</td>
                <td>{s['regions_success']}/{s['regions_total']}</td>
                <td>+{s['stations_added']} ~{s['stations_updated']}</td>
            </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FuelWatch — Статистика</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --primary: #2563eb;
            --primary-light: #3b82f6;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --dark: #1e293b;
            --gray: #64748b;
            --light: #f1f5f9;
            --white: #ffffff;
            --shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
            --shadow-lg: 0 20px 25px -5px rgba(0,0,0,0.1), 0 10px 10px -5px rgba(0,0,0,0.04);
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            color: var(--dark);
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            text-align: center;
            color: var(--white);
            margin-bottom: 30px;
            padding: 20px;
        }}
        .header h1 {{
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 8px;
            text-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }}
        .header p {{
            opacity: 0.9;
            font-size: 1.1rem;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .card {{
            background: var(--white);
            border-radius: 16px;
            padding: 24px;
            box-shadow: var(--shadow-lg);
            transition: transform 0.2s, box-shadow 0.2s;
            position: relative;
            overflow: hidden;
        }}
        .card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25);
        }}
        .card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: var(--primary);
        }}
        .card.success::before {{ background: var(--success); }}
        .card.warning::before {{ background: var(--warning); }}
        .card.danger::before {{ background: var(--danger); }}
        .card-icon {{
            font-size: 2.5rem;
            margin-bottom: 12px;
            display: block;
        }}
        .card-value {{
            font-size: 2.2rem;
            font-weight: 700;
            color: var(--dark);
            margin-bottom: 4px;
        }}
        .card-label {{
            color: var(--gray);
            font-size: 0.95rem;
            font-weight: 500;
        }}
        .card-sub {{
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid var(--light);
            font-size: 0.85rem;
            color: var(--gray);
        }}
        .section {{
            background: var(--white);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: var(--shadow-lg);
        }}
        .section h2 {{
            font-size: 1.3rem;
            margin-bottom: 20px;
            color: var(--dark);
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.95rem;
        }}
        th, td {{
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid var(--light);
        }}
        th {{
            font-weight: 600;
            color: var(--gray);
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        tr:hover td {{
            background: var(--light);
        }}
        .chart-container {{
            position: relative;
            height: 300px;
            margin: 20px 0;
        }}
        .footer {{
            text-align: center;
            color: var(--white);
            opacity: 0.7;
            padding: 20px;
            font-size: 0.9rem;
        }}
        code {{
            background: var(--light);
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'SF Mono', monospace;
            font-size: 0.85rem;
            color: var(--dark);
        }}
        @media (max-width: 768px) {{
            .header h1 {{ font-size: 1.8rem; }}
            .grid {{ grid-template-columns: 1fr; }}
            .card-value {{ font-size: 1.8rem; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⛽ FuelWatch</h1>
            <p>Панель администратора — {stats["generated_at"]}</p>
        </div>

        <div class="grid">
            <div class="card">
                <span class="card-icon">👥</span>
                <div class="card-value">{stats["total_users"]}</div>
                <div class="card-label">Уникальных пользователей</div>
                <div class="card-sub">
                    За 24ч: <strong>{stats["active_24h"]}</strong> &nbsp;|&nbsp;
                    За 7д: <strong>{stats["active_7d"]}</strong> &nbsp;|&nbsp;
                    За 30д: <strong>{stats["active_30d"]}</strong>
                </div>
            </div>
            <div class="card success">
                <span class="card-icon">⛽</span>
                <div class="card-value">{stats["active_stations"]}</div>
                <div class="card-label">Активных АЗС</div>
                <div class="card-sub">Всего в базе: <strong>{stats["total_stations"]}</strong></div>
            </div>
            <div class="card warning">
                <span class="card-icon">📝</span>
                <div class="card-value">{stats["total_updates"]}</div>
                <div class="card-label">Обновлений статусов</div>
                <div class="card-sub">От водителей сообщества</div>
            </div>
            <div class="card danger">
                <span class="card-icon">🔍</span>
                <div class="card-value">{stats["total_searches"]}</div>
                <div class="card-label">Поисковых запросов</div>
                <div class="card-sub">Геолокаций от пользователей</div>
            </div>
        </div>

        <div class="section">
            <h2>📊 Распределение по типам топлива</h2>
            <div class="chart-container">
                <canvas id="fuelTypeChart"></canvas>
            </div>
        </div>

        <div class="section">
            <h2>📊 Распределение по статусам</h2>
            <div class="chart-container">
                <canvas id="fuelStatusChart"></canvas>
            </div>
        </div>

        <div class="section">
            <h2>🏆 Топ-10 обновляторов (по ID)</h2>
            <table>
                <thead>
                    <tr><th>#</th><th>User ID</th><th>Обновлений</th></tr>
                </thead>
                <tbody>
                    {top_updaters_rows if top_updaters_rows else '<tr><td colspan="3" style="text-align:center;color:var(--gray)">Пока нет данных</td></tr>'}
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>🔄 Последние синхронизации</h2>
            <table>
                <thead>
                    <tr><th>Статус</th><th>ID</th><th>Начало</th><th>Регионов</th><th>Изменений</th></tr>
                </thead>
                <tbody>
                    {recent_syncs_rows if recent_syncs_rows else '<tr><td colspan="5" style="text-align:center;color:var(--gray)">Пока нет данных</td></tr>'}
                </tbody>
            </table>
        </div>

        <div class="footer">
            FuelWatch Bot &copy; 2026 — Генерировано автоматически
        </div>
    </div>

    <script>
        new Chart(document.getElementById('fuelTypeChart'), {{
            type: 'doughnut',
            data: {{
                labels: {fuel_type_labels},
                datasets: [{{
                    data: {fuel_type_values},
                    backgroundColor: ['#2563eb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'],
                    borderWidth: 0
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ position: 'bottom' }}
                }}
            }}
        }});

        new Chart(document.getElementById('fuelStatusChart'), {{
            type: 'bar',
            data: {{
                labels: {fuel_status_labels},
                datasets: [{{
                    label: 'Количество',
                    data: {fuel_status_values},
                    backgroundColor: ['#10b981', '#ef4444', '#f59e0b', '#6b7280'],
                    borderRadius: 8
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    y: {{ beginAtZero: true, ticks: {{ precision: 0 }} }}
                }}
            }}
        }});
    </script>
</body>
</html>"""

    filename = f"report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.html"
    path = REPORTS_DIR / filename
    path.write_text(html, encoding="utf-8")
    return path

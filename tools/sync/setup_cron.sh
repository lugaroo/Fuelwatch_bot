#!/bin/bash
# =============================================================================
# Настройка cron для синхронизации АЗС
# Путь: Fuelwatch_bot/data/tools/sync/setup_cron.sh
# =============================================================================

# Определяем корень проекта (3 уровня вверх от data/tools/sync/)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../../../" && pwd)"
LOG_DIR="$PROJECT_DIR/logs"
CRON_SCHEDULE="0 3 1 * *"  # 3:00 ночи, 1-го числа каждого месяца

echo "🔧 Настройка cron для FuelWatch Sync"
echo "   Проект: $PROJECT_DIR"
echo "   Логи:   $LOG_DIR"
echo "   Расписание: раз в месяц (1-е число, 3:00)"
echo ""

mkdir -p "$LOG_DIR"

CRON_CMD="$CRON_SCHEDULE cd $PROJECT_DIR && python3 data/tools/sync/run_sync.py >> $LOG_DIR/sync_$(date +\%Y\%m\%d).log 2>&1"

if crontab -l 2>/dev/null | grep -q "run_sync.py"; then
    echo "⚠️  Задача уже существует. Пропускаем."
else
    (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
    echo "✅ Задача добавлена."
fi

echo ""
echo "📋 Текущие задачи:"
crontab -l | grep -E "run_sync" || echo "   (нет)"

echo ""
echo "💡 Ручной запуск:"
echo "   python3 data/tools/sync/run_sync.py"
echo "💡 Статистика:"
echo "   python3 data/tools/sync/run_sync.py --stats"

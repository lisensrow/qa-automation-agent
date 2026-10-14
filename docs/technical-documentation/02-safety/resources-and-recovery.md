# Ресурсы, журнал операций и восстановление

Resource ledger хранится в Job. Тестовый объект имеет тип, имя, внешний ID, case-владельца, статус, metadata и зависимость на другие ресурсы. Идентичность известного объекта нельзя заменить другим ID только потому, что имя совпало.

Очищать можно только разрешённые owned/disposable объекты, по проверенному ID и предикатам области. Dependency order, пустота/связи и результат удаления должны проверяться. Ledger переживает сбой, но наличие ledger не гарантирует универсальный cleanup любого продукта.

Перед commit journal пишет intent с workflow/stage/resource, tool/arguments fingerprints и immutable oracle. Uncertain не означает «ничего не произошло». Сначала fresh native read и reconciliation, а не resend. Даже verified state не доказывает причинность отправки.

Native disabled до начала клика может дать not_sent; обычный JSON executed=false или timeout этого не доказывает. Operator-reviewed rejected/canceled сохраняют историю, не дают повторять ту же stage и не становятся verified/PASS.

Трёхстадийный explicit owned protocol существует, но полная автономная бизнес-приёмка, произвольный UI cleanup и legacy/unknown autosave остаются ограничениями. Удерживаемые пользователем демонстрационные коллекции не disposable и не удаляются автоматически.

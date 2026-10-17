# REGDMI638: owned-dmi-identity-baseline-v1

REGDMI638 owned-dmi-identity-baseline-v1 — закрытый запрос восьми несекретных identity-строк системы/BIOS/baseboard на выделенных Windows/Astra/core1.3.27 через существующий executeCommand1.4.0. Сначала собственный профиль/readiness; один fixed payload/Core WRITE/journal, own fresh full/hash/verification/report. Не доставка/обновление, не serial/UUID/CPU/DIMM inventory, не изменение BIOS/настроек/прав/безопасности/файлов. Нельзя переотправлять при uncertainty/rekey или повторять уже выполненные доставки. Это подготовка независимых наблюдений, НЕ smbiosAudit comparison/все SMBIOS структуры/UI/full-case PASS.

## Поля и будущая сырая гипотеза

| Native key | Windows projected CIM property | Astra fixed sysfs basename | Предлагаемый smbiosAudit путь |
| --- | --- | --- | --- |
| system_manufacturer | Win32_ComputerSystemProduct.Vendor | sys_vendor | data.system_information[].manufacturer |
| system_product_name | Win32_ComputerSystemProduct.Name | product_name | data.system_information[].product_name |
| system_product_version | Win32_ComputerSystemProduct.Version | product_version | data.system_information[].version |
| bios_vendor | Win32_BIOS.Manufacturer | bios_vendor | data.bios_information[].vendor |
| bios_version | Win32_BIOS.SMBIOSBIOSVersion | bios_version | data.bios_information[].version |
| baseboard_manufacturer | Win32_BaseBoard.Manufacturer | board_vendor | data.baseboard_information[].manufacturer |
| baseboard_product | Win32_BaseBoard.Product | board_name | data.baseboard_information[].product |
| baseboard_version | Win32_BaseBoard.Version | board_version | data.baseboard_information[].version |

owned-dmi-identity-baseline-v1 не выбирает по совпадению из нескольких строк: Windows требует по одному CIM instance каждого класса, иначе BLOCKED; Astra читает только восемь файлов /sys/class/dmi/id/, это primary identity projection, не полная enumeration всех firmware структур. Для будущего raw comparison каждая из трёх plugin arrays должна иметь ровно один объект, иначе ambiguous/BLOCKED, не выбрать подходящий элемент. Mapping выше — заранее объявленная ограниченная RAW ГИПОТЕЗА, не утверждённая спецификация представления UC. До smbiosAudit POST дополнительно закрепить фактические own baseline refs/hashes/raw expected и max_pair_seconds1800. Нет текущих ожидаемых строк до реального native запроса. Все8полей/unknown критерии фиксируются до запуска; нельзя убрать несовпавшее поле или нормализовать данные ради PASS.

Windows только Get-CimInstance -Property выбранных8строк; никаких Win32_Product/MSI/repair/serials/UUID. Linux только O_RDONLY/O_CLOEXEC/O_NOFOLLOW на конечных атрибутах,2048UTF8bytes/512chars максимум; decode error/missing/denied/oversized даёт unknown, не отсутствие устройства. У sysfs value убирается только конечный newline как терминатор строки файла; остальные пробелы/регистр и все plugin значения не нормализуются. Root class-directory symlink штатный, не меняется. Никакого исполнения содержимого файлов/произвольных shell paths.

JSON probe_version/platform/query_complete/values/error имеет exact schema; values содержит ровно8строк. Empty или placeholder-like (none,unknown,not specified,not applicable,default string,to be filled by o.e.m.) отмечаются unknown, raw value сохраняется; это консервативный критерий пригодности независимого identity, не переписывание значений. Частичный unknown → OBSERVED_WITH_UNKNOWNS, все8unknown либо failed query → BLOCKED, никакого zero/default/latest. Восемь usable → OBSERVED. Вывод/values SHA/native stdout SHA различать. Native success/identity/receipt не доказывает всех hardware/CPU/DIMM/UI полей или регресса.

## Основания и ограничения источников

Внешние первичные OS API references прочитаны17Oct2026: [ComputerSystemProduct](https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-computersystemproduct), [BIOS](https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-bios), [BaseBoard](https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-baseboard). Они определяют read-only свойства; BIOS Manufacturer/SMBIOSBIOSVersion относятся к SMBIOS vendor/version, Product у BaseBoard к Type2. Это внешняя OS reference, НЕ официальная UC спецификация/применимость к текущему frontend. Linux public v6.1 dmi-id.c source fetch в этом заходе не получен (timeout/cache miss); восемь sysfs paths проверяются как наблюдаемая гипотеза наличия, missing/denied остаются unknown. Не выдумывать успешное чтение источника или полную совместимость ядра.

Сохранённые US-T79/US-T102step5 содержат старые hardware examples, не текущий oracle. Операторский parse Windows example подтвердил category/key names; Astra example после HTML/NBSP обработки НЕ valid JSON (JSONDecodeError), автоматически чинить/принимать как executable request нельзя. Архив не менялся. Собственное636source reading/comprehension не стало исполнением, original559/631failures сохранены. Существующий smbiosAudit profile1.3.8 проверяет только3list fields, не все приведённые категории/значения. Старые15Oct deliveries/audits verified: Windows Job20261015-231219-5cb80093, Astra Job20261015-231332-733f6d8b — НЕ повторять доставку. Их own full READ уже имеет audit_data_summary.data_sha256; новая будущая fresh audit должна сохранять собственный полный data hash, а не требовать первый операторский hash как620.

## Приёмка контракта

Focused both-OS Core/OS/profile/hash/own full/journal/no-repeat/parser/unknown/raw spaces/runtime3statuses и Windows PowerShell syntax PASS; полный638301technical smoke gate проверяется ДО runtime. На этой ревизии real DMI baseline/новый smbiosAudit/value comparison ещё НЕ выполнены. Source/code/scope/oracle/standing approval transport и framework phases — операторская/системная подготовка, модельные вызовы отдельно. qwen3:14b/digest/context24576/5070Ti не менять, Jira/Zephyr запрещены. Версии текущей ОС/server/frontend/SMBIOSplugin сначала unknown до primary readiness, не latest. Полный source case остаётся BLOCKED. Actual outcomes сохранять отдельной новой памятью, эту contract revision после index не переписывать.

# REGOSPAIR624 — записанная пара native ОС / osAudit

## Применимость и предел

17 октября2026, Windows/Astra lab, core1.3.27, osAudit1.3.4, executeCommand1.4.0. Независимые значения Windows Win32_OperatingSystem:10.0.19045/build19045; Astra uname6.1.90-1-generic/x86_64, os-release VERSION_ID1.8_x86-64. Более точные build из inventory не независимо подтверждены; server/frontend версии в этом этапе unknown. qwen3:14b/context24576/5070Ti не менялись. Reviewed candidate/document_review о bounded runtime, НЕ verified истина продукта/полный regression. Добавлено0полных кейсов/шагов из40/301; Jira/Zephyr не открывались.

## Первичные доказательства

Native UQA612: Windows Job20261017-023455-efd8c39a/tc-e2044871/read ev-5be5aaf425a5; Astra Job20261017-023701-43537494/tc-f271c508/read ev-32dd027e4ae0. По одной verified executeCommand/own fresh full. ДО запроса объявлена будущая raw гипотеза: host_name против CSName на Windows; host_name против socket.gethostname и kernel_version против uname.release на Astra. Это НЕ утверждённый naming contract продукта.

UQA619 сама прочитала source step4, память и readiness, отправила по одной osAudit и получила own fresh full/legacy report. Windows Job20261017-025858-b2644951/tc-90b36f7e/cycle ev-222eec12e467/read ev-299e11591e53; Astra Job20261017-030103-0f1290d9/tc-467cfc9a/cycle ev-2c27849bd55e/read ev-db8d9341de8a. Обе операции verified, legacy report BLOCKED, исходные expected сохранены. ДО отправки закреплены ссылки612/native hashes/exact raw expected/max1800s/no normalization. Delivery/refresh/reinstall нет. Два Core WRITE подтверждения транспортированы оператором по standing разрешению пользователя, НЕ модельное решение о правах.

Первое полное data-SHA osAudit захватил ОПЕРАТОР позже, GET тех же задач: Job20261017-030543-8150541e/tc-0caedb08/cycle ev-d8a90fcd9fcb, Windows capture ev-53dd7a85db1f, Astra capture ev-1e869e053d62. Original619 read сохранял subset, НЕ полный data hash. Поэтому неизменность всего osAudit с момента original model read НЕ доказана. Проверены original subset/task identity/timestamps; private payload не публикуется. Ноль endpoint tasks/ops620.

UQA623 сама вызвала browser_compare_owned_os_identity_semantic, заново получила обе записанные задачи, проверила original native stdout/hash, поздний операторский data hash osAudit, original subset, verified journal links/task timestamps/pre-dispatch raw rule. Новых команд/операций на целях нет.

## Expected / actual

| ОС/поле | Ожидалось из612, raw | Получено из619, raw | Результат |
| --- | --- | --- | --- |
| Windows host_name | HOME-SERVER-UC- | home-server-UC-windows10 | RAW_DIFFERENT |
| Astra host_name | home-server-UC-astra18 | home-server-UC-astra18 | RAW_EQUAL |
| Astra kernel_version | 6.1.90-1-generic | 6.1.90-1-generic | RAW_EQUAL |

Windows623 Job20261017-033403-47dad5ac/tc-83a45b5d/cycle ev-e45651064879/compare ev-f5d9974dfa59: completed=true, raw MISMATCH/equal0/different1/unknown0. Astra623 Job20261017-033447-9cc05c44/tc-f33a83a9/cycle ev-e8475f3e6aef: completed=true, raw MATCH/equal2/different0/unknown0. Processed gaps1447.453s/1456.199s, исходный предел1800 не менялся. Это записанная пара, не live сейчас. Structured interpretation совпала с собственным receipt на обеих ОС; универсальная полнота свободного объяснения не заявляется.

CSName не обязательно то имя, которое продукт обязан возвращать: Windows различие НЕ developer-confirmed баг. Не обрезать/менять регистр/подменять expected ради PASS. Astra2matches не доказывает все OS поля/users/mounts/UI/source step. На обеих ОС full_source_case_status=BLOCKED; business_pass/full_case_passed/live_current_state_verified/developer_confirmed_bug/normalization_applied/same_audit_full_payload_as_original_model_read_proved=false. Новых agent tasks623=0, journal operations623=0.

## Механизм и роли

owned-os-identity-recorded-raw-v1 закрывает exact refs612/619/оператор620/predeclared raw mapping. Core OBSERVE/strict READ, две ОС, online/core/CI/agent/unchanged-source guards. Пустое/unknown поле даёт BLOCKED; отличие — MISMATCH гипотезы, не бизнес-FAIL. Изменение hashes/ссылок/окна/flags отказывает. Повторный GET не разрешает повторный POST.

Оператор подготовил code/scope/refs/oracle и первый полный osAudit data hash. Framework задавал каталог фаз, exact comparison и валидировал итог. Модель выбирала разрешённые вызовы, получала собственные ответы и формировала отчёт. Это bounded prepared continuation, НЕ обычный свободный вход/непрерывный самостоятельный lifecycle. Focused both-OS Core/hash/time/raw/unknown/privacy fixtures PASS; полный621297/297 technical PASS, не бизнес-PASS.

Повторное применение: использовать собственные фактические refs/hash и заранее объявленный текущий oracle; не переигрывать612/619 ради счётчика. Следом закрывать source-ordered semantic/UI gaps и самостоятельный выбор достаточных источников/инструментов без операторского покрокового каталога. Source608/597/604/614 ошибки и UI602 blocker сохранены, не затёрты новым успехом.

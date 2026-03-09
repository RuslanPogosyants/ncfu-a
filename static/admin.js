
let token = localStorage.getItem('token');
let currentGroup = null;
let currentDiscipline = null;
let schedulesByDate = {};
let currentUser = null;


if (!token) {
    window.location.href = '/login';
}


function logout() {
    localStorage.removeItem('token');
    window.location.href = '/login';
}


async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                ...options.headers,
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.status === 401) {
            logout();
            return null;
        }

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return response.json();
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}


async function loadUserInfo() {
    try {
        const user = await apiRequest('/api/me');
        if (user && user.full_name) {
            currentUser = user;
            document.getElementById('userName').textContent = user.full_name;
            if (user.role === 'admin') {
                const adminBtn = document.getElementById('adminPanelBtn');
                if (adminBtn) {
                    adminBtn.style.display = 'block';
                }
            }
        }
    } catch (error) {
        console.error('Ошибка загрузки информации о пользователе:', error);
        logout();
    }
}


async function loadGroups() {
    try {
        const groups = await apiRequest('/api/groups');
        if (!groups) return;

        const select = document.getElementById('groupSelect');
        select.innerHTML = '<option value="">Выберите группу</option>';
        groups.forEach(group => {
            const option = document.createElement('option');
            option.value = group.id;
            option.textContent = group.name;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Ошибка загрузки групп:', error);
        showNoData();
    }
}


async function loadDisciplinesForGroup(groupId) {
    try {
        const schedules = await apiRequest(`/api/schedules?group_id=${groupId}`);
        if (!schedules) {
            showNoData();
            return;
        }

        const disciplinesMap = new Map();
        schedules.forEach(schedule => {
            if (!disciplinesMap.has(schedule.discipline)) {
                disciplinesMap.set(schedule.discipline, {
                    id: schedule.discipline_id,
                    name: schedule.discipline
                });
            }
        });

        const disciplineSelect = document.getElementById('disciplineSelect');
        disciplineSelect.innerHTML = '<option value="">Выберите дисциплину</option>';
        disciplineSelect.disabled = false;

        disciplinesMap.forEach((discipline, name) => {
            const option = document.createElement('option');
            option.value = name;
            option.textContent = name;
            disciplineSelect.appendChild(option);
        });
    } catch (error) {
        console.error('Ошибка загрузки дисциплин:', error);
        showNoData();
    }
}


document.getElementById('groupSelect').addEventListener('change', async (e) => {
    currentGroup = e.target.value;
    currentDiscipline = null;

    if (currentGroup) {
        await loadDisciplinesForGroup(currentGroup);
    } else {
        document.getElementById('disciplineSelect').disabled = true;
        document.getElementById('disciplineSelect').innerHTML = '<option value="">Сначала выберите группу</option>';
        showNoData();
    }
});


document.getElementById('disciplineSelect').addEventListener('change', async (e) => {
    currentDiscipline = e.target.value;

    if (currentDiscipline && currentGroup) {
        await loadJournal();
    } else {
        showNoData();
    }
});


function showNoData() {
    document.getElementById('loading').style.display = 'none';
    document.getElementById('noData').style.display = 'block';
    document.getElementById('journalTable').style.display = 'none';
}


function showLoading() {
    document.getElementById('loading').style.display = 'block';
    document.getElementById('noData').style.display = 'none';
    document.getElementById('journalTable').style.display = 'none';
}


async function saveRecord(studentId, scheduleId, status, grade = null) {
    try {
        const formData = new URLSearchParams();
        formData.append('student_id', studentId);
        formData.append('schedule_id', scheduleId);
        formData.append('status', status || 'present');
        if (grade !== null && grade !== '') {
            formData.append('grade', grade);
        }

        await fetch('/api/records', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });
    } catch (error) {
        console.error('Ошибка сохранения записи:', error);
    }
}


async function loadJournal() {
    console.log('=== Начало загрузки журнала ===');
    showLoading();

    try {
        const schedules = await apiRequest(`/api/schedules?group_id=${currentGroup}`);
        console.log('Получено расписаний:', schedules ? schedules.length : 0);

        if (!schedules || schedules.length === 0) {
            showNoData();
            return;
        }

        const filteredSchedules = schedules.filter(s => s.discipline === currentDiscipline);
        console.log('Отфильтровано расписаний:', filteredSchedules.length);

        if (filteredSchedules.length === 0) {
            showNoData();
            return;
        }

        schedulesByDate = {};
        filteredSchedules.forEach(schedule => {
            const date = schedule.date;
            if (!schedulesByDate[date]) {
                schedulesByDate[date] = [];
            }
            schedulesByDate[date].push(schedule);
        });

        const students = await apiRequest(`/api/groups/${currentGroup}/students`);
        console.log('Получено студентов:', students ? students.length : 0);

        if (!students || students.length === 0) {
            showNoData();
            return;
        }

        const recordsPromises = filteredSchedules.map(schedule =>
            apiRequest(`/api/schedules/${schedule.id}/records`)
        );
        const allRecords = await Promise.all(recordsPromises);

        const recordsMap = {};
        allRecords.forEach((records, idx) => {
            if (!records) return;
            const scheduleId = filteredSchedules[idx].id;
            records.forEach(record => {
                const key = `${record.student_id}_${scheduleId}`;
                recordsMap[key] = record;
            });
        });

        console.log('Начинаем построение таблицы...');
        buildJournalTable(students, schedulesByDate, recordsMap, filteredSchedules);
        console.log('Таблица построена успешно');

        document.getElementById('loading').style.display = 'none';
        document.getElementById('noData').style.display = 'none';
        document.getElementById('journalTable').style.display = 'table';

        const uploadBtn = document.getElementById('uploadPhotoBtn');
        const hasEditableSchedules = filteredSchedules.some(s => s.can_edit && s.is_past);

        if (uploadBtn) {
            uploadBtn.style.display = hasEditableSchedules ? 'block' : 'none';
        }

        console.log('=== Журнал загружен успешно ===');
    } catch (error) {
        console.error('Ошибка загрузки журнала:', error);
        console.error('Stack:', error.stack);
        showNoData();
        console.log('Ошибка загрузки журнала: ' + error.message);
    }
}


function buildJournalTable(students, schedulesByDate, recordsMap, allSchedules) {
    console.log('buildJournalTable вызвана');

    const tableHead = document.getElementById('tableHead');
    const tableBody = document.getElementById('tableBody');

    if (!tableHead || !tableBody) {
        console.error('Не найдены элементы tableHead или tableBody');
        throw new Error('Не найдены элементы таблицы');
    }

    const canEditMap = {};
    allSchedules.forEach(schedule => {
        canEditMap[schedule.id] = schedule.can_edit;
    });

    const groupedStudents = {};
    students.forEach(student => {
        const groupName = student.group_name || 'Без группы';
        if (!groupedStudents[groupName]) {
            groupedStudents[groupName] = [];
        }
        groupedStudents[groupName].push(student);
    });

    const sortedDates = Object.keys(schedulesByDate).sort();

    sortedDates.forEach(date => {
        schedulesByDate[date].sort((a, b) => {
            return a.time_start.localeCompare(b.time_start);
        });
    });

    let headerHtml = '<tr><th rowspan="2">Студент</th>';

    sortedDates.forEach(date => {
        const lessonsCount = schedulesByDate[date].length;
        const dateObj = new Date(date + 'T00:00:00');
        const dateStr = dateObj.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' });
        headerHtml += `<th colspan="${lessonsCount}" class="date-header">${dateStr}</th>`;
    });

    const lessonTypes = new Set();
    Object.values(schedulesByDate).forEach(schedules => {
        schedules.forEach(schedule => lessonTypes.add(schedule.lesson_type));
    });
    const lessonTypesArray = Array.from(lessonTypes).sort();

    headerHtml += `<th colspan="${lessonTypesArray.length + 1}" class="date-header">Средние оценки</th>`;
    headerHtml += '</tr><tr>';

    sortedDates.forEach(date => {
        const schedulesInDay = schedulesByDate[date];

        schedulesInDay.forEach((schedule) => {
            const lessonType = schedule.lesson_type;
            const time = schedule.time_start;
            const discipline = schedule.discipline;
            const classroom = schedule.classroom;

            let editText = 'Только просмотр';
            if (schedule.is_cancelled) {
                editText = 'Занятие отменено';
            } else if (!schedule.is_past) {
                editText = 'Будущее занятие';
            } else if (schedule.can_edit) {
                editText = 'Редактирование доступно';
            } else {
                editText = 'Занятие другого преподавателя';
            }

            let headerTitle = `${discipline} (${classroom}) - ${editText}`;
            let headerText = '';

            if (schedulesInDay.length > 1) {
                headerText = `<div style="line-height: 1.3;">
                    <div>${lessonType}</div>
                    <div style="font-size: 10px; margin-top: 2px;">${time}</div>
                    <div style="font-size: 9px; margin-top: 2px; opacity: 0.9;">${classroom}</div>
                </div>`;
            } else {
                headerText = `${lessonType}<br>${time}`;
            }

            const canNavigate = !schedule.is_cancelled &&
                               (currentUser && (currentUser.role === 'admin' || schedule.can_edit));

            if (canNavigate) {
                headerHtml += `<th class="lesson-subheader clickable-lesson" title="${headerTitle} - Кликните для отметки посещаемости" style="min-width: ${schedulesInDay.length > 1 ? '70px' : '80px'}; cursor: pointer;" onclick="window.location.href='/attendance?schedule_id=${schedule.id}'">${headerText}</th>`;
            } else {
                headerHtml += `<th class="lesson-subheader" title="${headerTitle}" style="min-width: ${schedulesInDay.length > 1 ? '70px' : '80px'};">${headerText}</th>`;
            }
        });
    });

    lessonTypesArray.forEach(type => {
        headerHtml += `<th class="lesson-subheader">${type}</th>`;
    });
    headerHtml += `<th class="lesson-subheader">Общая</th>`;
    headerHtml += '</tr>';

    tableHead.innerHTML = headerHtml;

    let bodyHtml = '';

    Object.keys(groupedStudents).sort().forEach(groupName => {
        const groupStudents = groupedStudents[groupName];

        groupStudents.forEach((student) => {
            bodyHtml += '<tr>';
            bodyHtml += `<td class="student-name">${student.full_name}</td>`;

            const gradesByType = {};
            lessonTypesArray.forEach(type => gradesByType[type] = []);

            sortedDates.forEach(date => {
                const schedulesInDay = schedulesByDate[date];

                schedulesInDay.forEach((schedule) => {
                    const key = `${student.id}_${schedule.id}`;
                    const record = recordsMap[key] || { status: null, grade: null };
                    const canEdit = canEditMap[schedule.id];

                    let displayValue = '';
                    let cellClass = '';

                    if (record.grade) {
                        displayValue = record.grade;
                        cellClass = '';
                        if (!gradesByType[schedule.lesson_type]) {
                            gradesByType[schedule.lesson_type] = [];
                        }
                        gradesByType[schedule.lesson_type].push(parseFloat(record.grade));
                    } else if (record.status === 'absent') {
                        displayValue = 'Н';
                        cellClass = 'status-absent';
                    } else if (record.status === 'excused') {
                        displayValue = 'У';
                        cellClass = 'status-excused';
                    } else if (record.status === 'auto_detected') {
                        displayValue = 'Ф';
                        cellClass = 'status-auto';
                    } else if (record.status === 'fingerprint_detected') {
                        displayValue = 'О';
                        cellClass = 'status-fingerprint';
                    }

                    const readonlyAttr = canEdit ? '' : 'readonly';
                    const disabledClass = canEdit ? '' : 'readonly-cell';
                    const pairInfo = `${schedule.discipline} (${schedule.classroom}) ${schedule.time_start}`;

                    bodyHtml += `<td class="status-cell ${disabledClass}" title="${pairInfo}">
                        <input type="text" class="status-input ${cellClass}" value="${displayValue}" maxlength="4" data-student-id="${student.id}" data-schedule-id="${schedule.id}" data-can-edit="${canEdit}" placeholder="-" ${readonlyAttr}>
                    </td>`;
                });
            });

            let allGrades = [];
            lessonTypesArray.forEach(type => {
                const grades = gradesByType[type] || [];
                if (grades.length > 0) {
                    const avg = grades.reduce((a, b) => a + b, 0) / grades.length;
                    bodyHtml += `<td class="average-cell">${avg.toFixed(2)}</td>`;
                    allGrades.push(...grades);
                } else {
                    bodyHtml += `<td class="average-cell">-</td>`;
                }
            });

            if (allGrades.length > 0) {
                const totalAvg = allGrades.reduce((a, b) => a + b, 0) / allGrades.length;
                bodyHtml += `<td class="average-cell total-average">${totalAvg.toFixed(2)}</td>`;
            } else {
                bodyHtml += `<td class="average-cell total-average">-</td>`;
            }

            bodyHtml += '</tr>';
        });
    });

    tableBody.innerHTML = bodyHtml;
    attachEventHandlers();
    console.log('Таблица построена, обработчики добавлены');
}


function updateAverages(studentId) {
    const studentRow = document.querySelector(`tr:has(input[data-student-id="${studentId}"])`);
    if (!studentRow) return;

    const inputs = studentRow.querySelectorAll('.status-input');
    const gradesByType = {};

    inputs.forEach(input => {
        const scheduleId = input.dataset.scheduleId;
        const schedule = Object.values(schedulesByDate).flat().find(s => s.id == scheduleId);
        if (!schedule) return;

        const value = input.value.trim();
        if (value && value !== 'Н' && value !== 'У' && value !== 'А' && value !== '-') {
            const grade = parseFloat(value.replace(',', '.'));
            if (!isNaN(grade)) {
                if (!gradesByType[schedule.lesson_type]) {
                    gradesByType[schedule.lesson_type] = [];
                }
                gradesByType[schedule.lesson_type].push(grade);
            }
        }
    });

    const lessonTypes = Array.from(document.querySelectorAll('.lesson-subheader'))
        .map(th => th.textContent.trim())
        .filter(text => text && !text.includes(':') && text !== 'Общая');

    const averageCells = studentRow.querySelectorAll('.average-cell');
    let allGrades = [];

    lessonTypes.forEach((type, index) => {
        if (averageCells[index]) {
            const grades = gradesByType[type] || [];
            if (grades.length > 0) {
                const avg = grades.reduce((a, b) => a + b, 0) / grades.length;
                averageCells[index].textContent = avg.toFixed(2);
                allGrades.push(...grades);
            } else {
                averageCells[index].textContent = '-';
            }
        }
    });

    const totalAvgCell = studentRow.querySelector('.total-average');
    if (totalAvgCell) {
        if (allGrades.length > 0) {
            const totalAvg = allGrades.reduce((a, b) => a + b, 0) / allGrades.length;
            totalAvgCell.textContent = totalAvg.toFixed(2);
        } else {
            totalAvgCell.textContent = '-';
        }
    }
}


function attachEventHandlers() {
    document.querySelectorAll('.status-input').forEach(input => {
        const canEdit = input.dataset.canEdit === 'true';

        if (!canEdit) {
            input.style.cursor = 'not-allowed';
            input.title = 'Только просмотр';
            return;
        }

        input.addEventListener('blur', async (e) => {
            const value = e.target.value.trim();
            const studentId = e.target.dataset.studentId;
            const scheduleId = e.target.dataset.scheduleId;

            let status = null;
            let grade = null;

            if (value === '' || value === '-') {
                status = null;
                grade = null;
            } else if (value === 'Н' || value === 'н') {
                status = 'absent';
                grade = null;
                e.target.value = 'Н';
                e.target.className = 'status-input status-absent';
            } else if (value === 'У' || value === 'у') {
                status = 'excused';
                grade = null;
                e.target.value = 'У';
                e.target.className = 'status-input status-excused';
            } else if (value === 'Ф' || value === 'ф') {
                status = 'auto_detected';
                grade = null;
                e.target.value = 'Ф';
                e.target.className = 'status-input status-auto';
            } else if (value === 'О' || value === 'о') {
                status = 'fingerprint_detected';
                grade = null;
                e.target.value = 'О';
                e.target.className = 'status-input status-fingerprint';
            } else {
                const sanitized = value.replace(',', '.');
                const numValue = Number(sanitized);
                if (
                    !Number.isNaN(numValue) &&
                    Number.isInteger(numValue) &&
                    numValue >= 2 &&
                    numValue <= 5
                ) {
                    status = null;
                    grade = numValue;
                    e.target.className = 'status-input';
                } else {
                    console.log('Оценка должна быть целым числом от 2 до 5');
                    e.target.value = '';
                    e.target.className = 'status-input';
                    return;
                }
            }

            await saveRecord(studentId, scheduleId, status, grade);
            updateAverages(studentId);
        });

        input.addEventListener('dblclick', async (e) => {
            const currentValue = e.target.value.trim();
            const studentId = e.target.dataset.studentId;
            const scheduleId = e.target.dataset.scheduleId;

            let newValue, status, grade;

            if (currentValue === '' || currentValue === '-' || (!isNaN(parseFloat(currentValue)))) {
                newValue = 'Н';
                status = 'absent';
                grade = null;
                e.target.className = 'status-input status-absent';
            } else if (currentValue === 'Н') {
                newValue = 'У';
                status = 'excused';
                grade = null;
                e.target.className = 'status-input status-excused';
            } else {
                newValue = '';
                status = null;
                grade = null;
                e.target.className = 'status-input';
            }

            e.target.value = newValue;
            await saveRecord(studentId, scheduleId, status, grade);
            updateAverages(studentId);
        });
    });
}



let selectedPhoto = null;
let currentScheduleForRecognition = null;

function initPhotoUpload() {
    const modal = document.getElementById('uploadModal');
    const btn = document.getElementById('uploadPhotoBtn');
    const closeBtn = modal ? modal.querySelector('.close') : null;
    const uploadArea = document.getElementById('uploadArea');
    const photoInput = document.getElementById('photoInput');
    const photoPreview = document.getElementById('photoPreview');
    const recognizeBtn = document.getElementById('recognizeBtn');
    const selectDate = document.getElementById('selectDate');
    const selectSchedule = document.getElementById('selectSchedule');
    const selectScheduleGroup = document.getElementById('selectScheduleGroup');

    if (!modal || !btn) {
        console.warn('Модальное окно загрузки фото не найдено');
        return;
    }

    btn.onclick = () => {
        modal.style.display = 'block';
        selectedPhoto = null;
        if (photoPreview) photoPreview.style.display = 'none';
        if (recognizeBtn) recognizeBtn.disabled = true;
        if (uploadArea) uploadArea.style.display = 'none';
        if (selectScheduleGroup) selectScheduleGroup.style.display = 'none';
        const statsDiv = document.getElementById('recognitionStats');
        if (statsDiv) statsDiv.style.display = 'none';
        populateDates();
    };

    if (selectDate) {
        selectDate.onchange = () => {
            const date = selectDate.value;
            if (date) {

                if (schedulesByDate[date]) {
                    populateSchedulesForDate(date);
                    if (selectScheduleGroup) selectScheduleGroup.style.display = 'block';
                    if (uploadArea) uploadArea.style.display = 'none';
                    if (photoPreview) photoPreview.style.display = 'none';
                    if (recognizeBtn) recognizeBtn.disabled = true;
                    selectedPhoto = null;
                    const statsDiv = document.getElementById('recognitionStats');
                    if (statsDiv) statsDiv.style.display = 'none';
                } else {
                    console.log('На выбранную дату нет занятий. Пожалуйста, выберите другую дату.');
                    selectDate.value = '';
                    if (selectScheduleGroup) selectScheduleGroup.style.display = 'none';
                    if (uploadArea) uploadArea.style.display = 'none';
                }
            } else {
                if (selectScheduleGroup) selectScheduleGroup.style.display = 'none';
                if (uploadArea) uploadArea.style.display = 'none';
            }
        };
    }

    if (selectSchedule) {
        selectSchedule.onchange = () => {
            const scheduleId = selectSchedule.value;
            if (scheduleId) {
                currentScheduleForRecognition = scheduleId;
                if (uploadArea) uploadArea.style.display = 'block';
            } else {
                if (uploadArea) uploadArea.style.display = 'none';
            }
        };
    }

    if (closeBtn) {
        closeBtn.onclick = () => {
            modal.style.display = 'none';
        };
    }

    window.onclick = (event) => {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    };

    if (uploadArea) {
        uploadArea.onclick = () => {
            if (photoInput) photoInput.click();
        };

        uploadArea.ondragover = (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragging');
        };

        uploadArea.ondragleave = () => {
            uploadArea.classList.remove('dragging');
        };

        uploadArea.ondrop = (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragging');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handlePhotoSelect(files[0]);
            }
        };
    }

    if (photoInput) {
        photoInput.onchange = (e) => {
            if (e.target.files.length > 0) {
                handlePhotoSelect(e.target.files[0]);
            }
        };
    }

    if (recognizeBtn) {
        recognizeBtn.onclick = async () => {
            await performRecognition();
        };
    }
}

function populateDates() {
    const selectDate = document.getElementById('selectDate');
    const dateHint = document.getElementById('dateHint');
    if (!selectDate) return;


    const availableDates = Object.keys(schedulesByDate)
        .filter(date => {
            const schedules = schedulesByDate[date];

            return schedules.some(s => s.can_edit && s.is_past);
        })
        .sort();

    if (availableDates.length > 0) {

        selectDate.min = availableDates[0];
        selectDate.max = availableDates[availableDates.length - 1];
        selectDate.disabled = false;


        const minDateObj = new Date(availableDates[0] + 'T00:00:00');
        const maxDateObj = new Date(availableDates[availableDates.length - 1] + 'T00:00:00');
        const minDateStr = minDateObj.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' });
        const maxDateStr = maxDateObj.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' });

        if (dateHint) {
            dateHint.textContent = `Доступные даты: с ${minDateStr} по ${maxDateStr} (только прошедшие занятия)`;
            dateHint.className = 'date-hint';
        }
    } else {
        if (dateHint) {
            dateHint.textContent = 'Нет доступных дат для загрузки фото (нет прошедших занятий)';
            dateHint.className = 'date-hint warning';
        }
        selectDate.disabled = true;
    }


    selectDate.value = '';
}

function populateSchedulesForDate(date) {
    const selectSchedule = document.getElementById('selectSchedule');
    const uploadArea = document.getElementById('uploadArea');
    if (!selectSchedule) return;

    selectSchedule.innerHTML = '<option value="">Выберите пару</option>';
    const schedules = schedulesByDate[date];
    if (!schedules) return;


    const editableSchedules = schedules.filter(s => s.can_edit && s.is_past);
    let hasOptions = false;

    schedules.forEach((schedule) => {
        const option = document.createElement('option');
        option.value = schedule.id;

        let text = `${schedule.lesson_type} ${schedule.time_start}`;
        if (schedules.length > 1) {
            text += ` (${schedule.classroom})`;
        }

        if (!schedule.can_edit) {
            text += ' - только просмотр';
            option.disabled = true;
        } else if (!schedule.is_past) {
            text += ' - будущее занятие';
            option.disabled = true;
        } else {
            hasOptions = true;
        }

        option.textContent = text;
        selectSchedule.appendChild(option);
    });


    if (editableSchedules.length === 1) {
        selectSchedule.value = editableSchedules[0].id;
        currentScheduleForRecognition = editableSchedules[0].id;
        if (uploadArea) uploadArea.style.display = 'block';


        const dateHint = document.getElementById('dateHint');
        if (dateHint) {
            dateHint.textContent = `Автоматически выбрана единственная доступная пара: ${editableSchedules[0].lesson_type} в ${editableSchedules[0].time_start}`;
            dateHint.className = 'date-hint';
        }
    } else if (editableSchedules.length === 0) {
        const dateHint = document.getElementById('dateHint');
        if (dateHint) {
            dateHint.textContent = 'На выбранную дату нет доступных для редактирования пар';
            dateHint.className = 'date-hint warning';
        }
        selectSchedule.disabled = true;
    } else {
        const dateHint = document.getElementById('dateHint');
        if (dateHint) {
            dateHint.textContent = `На выбранную дату найдено занятий: ${editableSchedules.length}. Выберите нужную пару.`;
            dateHint.className = 'date-hint';
        }
        selectSchedule.disabled = false;
    }
}

function handlePhotoSelect(file) {
    if (!file.type.startsWith('image/')) {
        console.log('Пожалуйста, выберите изображение');
        return;
    }

    selectedPhoto = file;

    const reader = new FileReader();
    reader.onload = (e) => {
        const photoPreview = document.getElementById('photoPreview');
        const recognizeBtn = document.getElementById('recognizeBtn');
        if (photoPreview) {
            photoPreview.src = e.target.result;
            photoPreview.style.display = 'block';
        }
        if (recognizeBtn) {
            recognizeBtn.disabled = false;
        }
    };
    reader.readAsDataURL(file);
}

async function performRecognition() {
    if (!selectedPhoto || !currentScheduleForRecognition) {
        console.log('Ошибка: не выбрано фото или занятие');
        return;
    }

    const recognizeBtn = document.getElementById('recognizeBtn');
    if (recognizeBtn) {
        recognizeBtn.disabled = true;
        recognizeBtn.textContent = 'Распознавание...';
    }

    try {
        const formData = new FormData();
        formData.append('file', selectedPhoto);

        const response = await fetch(`/api/schedules/${currentScheduleForRecognition}/recognize-attendance`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });

        if (!response.ok) {
            throw new Error('Ошибка при распознавании');
        }

        const result = await response.json();

        const recognizedCount = document.getElementById('recognizedCount');
        const totalFaces = document.getElementById('totalFaces');
        const recognitionRate = document.getElementById('recognitionRate');
        const recognitionStats = document.getElementById('recognitionStats');

        if (recognizedCount) recognizedCount.textContent = `${result.recognized_count} из ${result.total_students}`;
        if (totalFaces) totalFaces.textContent = result.total_faces;
        if (recognitionRate) recognitionRate.textContent = result.recognition_rate;
        if (recognitionStats) recognitionStats.style.display = 'block';

        await loadJournal();

        console.log(`Успешно распознано ${result.recognized_count} студентов из ${result.total_students}`);

        setTimeout(() => {
            const modal = document.getElementById('uploadModal');
            if (modal) modal.style.display = 'none';
        }, 2000);

    } catch (error) {
        console.error('Ошибка распознавания:', error);
        console.log('Ошибка при распознавании лиц. Попробуйте еще раз.');
    } finally {
        if (recognizeBtn) {
            recognizeBtn.disabled = false;
            recognizeBtn.textContent = 'Распознать и отметить посещаемость';
        }
    }
}



function searchInTable(query) {
    const table = document.getElementById('journalTable');
    const tbody = document.getElementById('tableBody');

    if (!table || !tbody || !query) {

        if (tbody) {
            const rows = tbody.querySelectorAll('tr');
            rows.forEach(row => {
                row.style.display = '';
            });
        }
        return;
    }

    const searchLower = query.toLowerCase().trim();
    const rows = tbody.querySelectorAll('tr');
    let visibleCount = 0;

    rows.forEach(row => {

        const studentNameCell = row.querySelector('.student-name');
        if (studentNameCell) {
            const studentName = studentNameCell.textContent.toLowerCase();

            if (studentName.includes(searchLower)) {
                row.style.display = '';
                visibleCount++;
            } else {
                row.style.display = 'none';
            }
        }
    });


    if (visibleCount === 0 && rows.length > 0) {
        toast.info(`Студенты с "${query}" не найдены`, 'Поиск');
    }
}


document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM загружен, инициализация...');
    loadUserInfo();
    loadGroups();
    showNoData();
    initPhotoUpload();
});


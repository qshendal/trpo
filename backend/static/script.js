document.addEventListener('DOMContentLoaded', () => {
    // --- ЭЛЕМЕНТЫ УПРАВЛЕНИЯ ---
    const authShell = document.getElementById("authShell");
    const showRegister = document.getElementById("showRegister");
    const showLogin = document.getElementById("showLogin");
    const regForm = document.getElementById("regForm");
    const loginForm = document.querySelector(".auth-login form");

    // --- 1. ПЕРЕКЛЮЧЕНИЕ ФОРМ (АНИМАЦИЯ) ---
    if (authShell && showRegister && showLogin) {
        showRegister.addEventListener("click", () => authShell.classList.add("active"));
        showLogin.addEventListener("click", () => authShell.classList.remove("active"));
    }

    // --- 2. ВАЛИДАЦИЯ РЕГИСТРАЦИИ ---
    if (regForm) {
        regForm.addEventListener("submit", (e) => {
            const name = document.getElementById("regName").value.trim();
            const email = document.getElementById("regEmail").value.trim();
            const password = document.getElementById("regPass").value;
            const confirm = document.getElementById("confirm").value;
            
            let errors = [];

            // Проверка имени (только буквы, цифры и пробелы, от 2 до 30 символов)
            const nameRegex = /^[a-zA-Z0-9а-яА-ЯёЁ\s]{2,30}$/;
            if (!nameRegex.test(name)) {
                errors.push("Имя должно быть от 2 до 30 символов и не содержать спецсимволы.");
            }

            // Проверка Email (стандартный паттерн)
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(email)) {
                errors.push("Введите корректный адрес электронной почты.");
            }

            // Проверка сложности пароля (минимум 6 символов, хотя бы одна буква и одна цифра)
            const passRegex = /^(?=.*[A-Za-zА-Яа-я])(?=.*\d).{6,}$/;
            if (!passRegex.test(password)) {
                errors.push("Пароль должен быть не менее 6 символов и содержать хотя бы одну букву и одну цифру.");
            }

            // Сравнение паролей
            if (password !== confirm) {
                errors.push("Пароли не совпадают.");
            }

            if (errors.length > 0) {
                e.preventDefault();
                alert("Ошибка регистрации:\n\n• " + errors.join("\n• "));
            }
        });
    }

    // --- 3. ВАЛИДАЦИЯ ВХОДА ---
    if (loginForm) {
        loginForm.addEventListener("submit", (e) => {
            const name = document.getElementById("loginName").value.trim();
            const password = document.getElementById("loginPass").value.trim();

            if (!name || !password) {
                e.preventDefault();
                alert("Пожалуйста, заполните все поля для входа.");
            }
        });
    }

    // --- 4. АНИМАЦИЯ ПОЛЕЙ (Floating Labels) ---
    document.querySelectorAll(".auth-field").forEach(field => {
        const input = field.querySelector(".auth-input");

        const updateState = () => {
            if (input.value.trim() !== "") {
                field.classList.add("active");
            } else {
                field.classList.remove("active");
            }
        };

        input.addEventListener("focus", () => field.classList.add("active"));
        input.addEventListener("blur", updateState);
        
        // Проверка при загрузке (если автозаполнение сработало)
        updateState();
    });
});

// Глобальная функция переключения видимости пароля
window.togglePassword = () => {
    const fields = [document.getElementById("regPass"), document.getElementById("confirm"), document.getElementById("loginPass")];
    fields.forEach(f => {
        if (f) f.type = (f.type === "password") ? "text" : "password";
    });
};
const form = document.getElementById("regForm");

form.addEventListener("submit", function (e) {
  const pwd = document.getElementById("password").value;
  const confirm = document.getElementById("confirm").value;
  if (pwd !== confirm) {
    e.preventDefault();
    alert("Пароли не совпадают. Проверьте ввод.");
  }
});

function togglePassword() {
  const pwd = document.getElementById("password");
  const confirm = document.getElementById("confirm");
  const type = pwd.type === "password" ? "text" : "password";
  pwd.type = type;
  confirm.type = type;
}
document.querySelectorAll(".auth-field").forEach(field => {
  const input = field.querySelector(".auth-input");

  input.addEventListener("focus", () => {
    field.classList.add("active");
  });

  input.addEventListener("blur", () => {
    if (input.value.trim() === "") {
      field.classList.remove("active");
    }
  });

  if (input.value.trim() !== "") {
    field.classList.add("active");
  }
});
const authShell = document.getElementById('authShell');
const registerBtn = document.getElementById('showRegister');
const loginBtn = document.getElementById('showLogin');

registerBtn.addEventListener('click', () => {
  authShell.classList.add('active');
});

loginBtn.addEventListener('click', () => {
  authShell.classList.remove('active');
});
document.addEventListener('DOMContentLoaded', () => {
  const loginForm = document.querySelector('.auth-login form');

  loginForm.addEventListener('submit', (e) => {
    e.preventDefault();

    const email = document.getElementById('loginEmail').value.trim();
    const password = document.getElementById('loginPass').value.trim();

    const adminEmail = 'admin@techservice.com';
    const adminPassword = 'admin123';
    
    if (email === adminEmail && password === adminPassword) {
      location.href = 'Панель управления.html';
    } else {
      location.href = 'пользователь.html'; // Обычный пользователь — панель действий
    }
  });
});

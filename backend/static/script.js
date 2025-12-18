document.addEventListener('DOMContentLoaded', () => {
  const regForm = document.getElementById("regForm");
  if (regForm) {
    regForm.addEventListener("submit", (e) => {
      const password = document.getElementById("regPass").value;
      const confirm = document.getElementById("confirm").value;
      if (password !== confirm) {
        e.preventDefault();
        alert("Пароли не совпадают. Проверьте ввод.");
      }
    });
  }

  window.togglePassword = () => {
    const password = document.getElementById("regPass");
    const confirm = document.getElementById("confirm");
    const type = password.type === "password" ? "text" : "password";
    password.type = type;
    confirm.type = type;
  };

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

  const authShell = document.getElementById("authShell");
  const showRegister = document.getElementById("showRegister");
  const showLogin = document.getElementById("showLogin");

  if (authShell && showRegister && showLogin) {
    showRegister.addEventListener("click", () => {
      authShell.classList.add("active");
    });

    showLogin.addEventListener("click", () => {
      authShell.classList.remove("active");
    });
  }

  const loginForm = document.querySelector(".auth-login form");
  if (loginForm) {
    loginForm.addEventListener("submit", (e) => {
      const name = document.getElementById("loginName").value.trim();
      const password = document.getElementById("loginPass").value.trim();

      if (!name || !password) {
        e.preventDefault();
        alert("Введите имя и пароль.");
      }
    });
  }
});
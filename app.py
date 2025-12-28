from flask import Flask, render_template, request, redirect, session, url_for
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = "super_secret_key"

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)
# ---------------- HOME ----------------
@app.route("/", methods=["GET", "POST"])
def home():
    if "user" not in session:
        return redirect("/login")

    login = session["user"]["login"]

    # ➕ Додавання витрат
    if request.method == "POST" and request.form.get("type") == "expense":
        supabase.table("expenses").insert({
            "login": login,
            "category": request.form["category"],
            "suma": request.form["suma"]
        }).execute()
        return redirect("/")

    # Дані користувача
    user_data = supabase.table("users").select("*").eq("login", login).execute().data[0]

    # Витрати
    expenses = supabase.table("expenses").select("*").eq("login", login).execute().data
    total_expenses = sum(int(e["suma"]) for e in expenses)

    # Додатковий дохід
    additional_income = supabase.table("additional_income").select("*").eq("login", login).execute().data
    total_additional_income = sum(int(i["suma"]) for i in additional_income)

    # Загальний баланс
    total_balance = user_data["salary"] + total_additional_income - total_expenses

    return render_template(
        "base.html",
        user=user_data,  # Передаємо юзера в сесію
        expenses=expenses,
        total=total_expenses,
        additional_income=additional_income,
        total_additional_income=total_additional_income,
        total_balance=total_balance
    )

# ---------------- ДОХІД ----------------
@app.route("/add-income", methods=["POST"])
def add_income():
    if "user" not in session:
        return redirect("/login")

    login = session["user"]["login"]
    amount = int(request.form["amount"])

    # додаємо до salary
    new_salary = int(session["user"]["salary"]) + amount

    supabase.table("users").update({
        "salary": new_salary
    }).eq("login", login).execute()

    session["user"]["salary"] = new_salary
    return redirect("/")


# ---------------- ДОДАТКОВИЙ ДОХІД ----------------
@app.route("/add-additional-income", methods=["POST"])
def add_additional_income():
    if "user" not in session:
        return redirect("/login")

    login = session["user"]["login"]
    category = request.form["category"]
    suma = int(request.form["suma"])

    supabase.table("additional_income").insert({
        "login": login,
        "category": category,
        "suma": suma
    }).execute()

    # Оновлюємо зарплату користувача
    # new_salary = int(session["user"]["salary"]) + suma
    # supabase.table("users").update({"salary": new_salary}) \
    #     .eq("login", login).execute()
    # session["user"]["salary"] = new_salary

    return redirect("/")



# ---------------- PROFILE ----------------
@app.route("/update-profile", methods=["POST"])
def update_profile():
    supabase.table("users").update({
        "country": request.form["country"],
        "salary": request.form["salary"]
    }).eq("login", session["user"]["login"]).execute()

    session["user"]["country"] = request.form["country"]
    session["user"]["salary"] = request.form["salary"]

    return redirect("/")


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = supabase.table("users").select("*") \
            .eq("login", request.form["login"]) \
            .eq("password", request.form["password"]) \
            .execute().data

        if not user:
            return "Невірний логін або пароль"

        session["user"] = user[0]  # Зберігаємо юзера в сесію
        return redirect("/")

    return render_template("base.html")  # Тут юзер ще не визначений

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        supabase.table("users").insert({
            "login": request.form["login"],
            "password": request.form["password"],
            "country": "",
            "salary": 0
        }).execute()
        return redirect("/login")

    return render_template("base.html")  # Тут юзер ще не визначений

# ---------------- STATS ----------------
@app.route("/stats", methods=["GET"])
def stats():
    if "user" not in session:
        return redirect("/login")

    login = session["user"]["login"]
    user_data = supabase.table("users").select("*").eq("login", login).execute().data[0]

    # Витрати
    expenses = supabase.table("expenses").select("*").eq("login", login).execute().data
    total_expenses = sum(int(e["suma"]) for e in expenses)

    # Додатковий дохід
    additional_income = supabase.table("additional_income").select("*").eq("login", login).execute().data
    total_additional_income = sum(int(i["suma"]) for i in additional_income)

    salary = int(user_data["salary"])
    mysterious_income = salary + total_additional_income

    # Витрати по категоріях
    categories_summary = {}
    for e in expenses:
        cat = e["category"]
        categories_summary[cat] = categories_summary.get(cat, 0) + int(e["suma"])
    categories_percent = {cat: round((amount / mysterious_income) * 100, 2) 
                          for cat, amount in categories_summary.items()}

    remaining = mysterious_income - total_expenses

    return render_template(
        "base.html",
        user=user_data,
        stats=True,
        mysterious_income=mysterious_income,
        categories_summary=categories_summary,
        categories_percent=categories_percent,
        remaining=remaining,
        total_expenses=total_expenses,
        total_additional_income=total_additional_income
    )


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    app.run(host='0.0.0.0',port=int(os.environ.get('PORT',5000)), debug=True)

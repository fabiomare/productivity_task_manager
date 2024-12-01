# Productivity Task Manager

## How to Run the Application

1. Install dependencies
```bash
pip install fastapi uvicorn pydantic sqlalchemy sqlite3
```
2. Clone the repository to your local machine and navigate into the project directory:
```bash
git clone https://github.com/your-username/productivity_task_manager.git
cd productivity_task_manager
```
3. Run the `main.py` file using uvicorn:
```bash
uvicorn main:app --reload
```
4. Open your browser and visit http://127.0.0.1:8000/todos to access the application.


## Project Files Description


`main.py` defines the FastAPI application, database models, routes, and logic for managing to-do items. Key functionalities include:
- Adding, updating, and deleting tasks.
- Marking tasks as done and organizing them by status and priority.
- Providing both HTML-based views and API endpoints.

`templates/index_root.html`
The landing page template rendered at the root (`/`). It serves as an introduction or homepage for the application, offering navigation links.

`templates/index_todos.html`
The main to-do management page. It dynamically displays tasks organized into **Active** and **Done** sections, and includes interactive options for marking tasks as done or deleting them.

`todos.db`
The SQLite database file where all to-do items are stored. This is automatically generated and updated by the application based on user actions.

---

## Future Works

- To improve tasks manager
- To introduce Pomodoro technique timers 

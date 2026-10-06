from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import auth, projects, issues, comments, activity, attachments, sprints, webhooks, analytics, export
app = FastAPI(
    title="BugFlow API",
    version="1.0.0",
    description="BugFlow - Issue Tracking & Resolution Platform"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(issues.router)
app.include_router(comments.router)
app.include_router(activity.router)
app.include_router(attachments.router)
app.include_router(sprints.router)
app.include_router(webhooks.router)
app.include_router(analytics.router)
app.include_router(export.router) 

@app.get("/")
def root():
    return {
        "message": "BugFlow API is running"
    }
const API_URL = "http://127.0.0.1:8000";
const TOKEN = localStorage.getItem("bugflow_token");

let currentIssueId = null;


// ===============================
// LOAD ISSUES
// ===============================

async function loadIssues() {

    try {

        const response = await fetch(
            `${API_URL}/api/v1/issues/`,
            {
                headers: {
                    "Authorization": `Bearer ${TOKEN}`
                }
            }
        );

        if (!response.ok) {
            throw new Error("Failed to load issues");
        }

        const issues = await response.json();

        displayIssues(issues);
        updateStatistics(issues);

    } catch (error) {

        console.error(error);

        document.getElementById("issueTable").innerHTML = `
            <tr>
                <td colspan="7"
                    class="text-center py-8 text-red-500">
                    Failed to load issues
                </td>
            </tr>
        `;
    }
}


// ===============================
// DISPLAY ISSUES
// ===============================

function displayIssues(issues) {

    const table = document.getElementById("issueTable");

    table.innerHTML = "";

    if (issues.length === 0) {

        table.innerHTML = `
            <tr>
                <td colspan="7"
                    class="text-center py-8 text-gray-500">
                    No issues found
                </td>
            </tr>
        `;

        return;
    }


    issues.forEach(issue => {

        const row = document.createElement("tr");

        row.className = "border-t";

        row.innerHTML = `
            <td class="px-5 py-3">
                ${issue.issue_key || "-"}
            </td>

            <td class="px-5 py-3">
                ${issue.title || "-"}
            </td>

            <td class="px-5 py-3">
                ${issue.severity || "-"}
            </td>

            <td class="px-5 py-3">
                ${issue.priority || "-"}
            </td>

            <td class="px-5 py-3">
                <span class="bg-gray-100 px-2 py-1 rounded text-xs">
                    ${issue.status || "-"}
                </span>
            </td>

            <td class="px-5 py-3">
                ${issue.assignee_id || "Unassigned"}
            </td>

            <td class="px-5 py-3">
                <button
                    onclick="viewIssue(${issue.id})"
                    class="bg-gray-800 text-white px-3 py-1 rounded text-sm hover:bg-gray-700"
                >
                    View
                </button>
            </td>
        `;

        table.appendChild(row);

    });
}
// ===============================
// STATISTICS
// ===============================

function updateStatistics(issues) {

    document.getElementById("totalIssues").textContent =
        issues.length;

    document.getElementById("reportedIssues").textContent =
        issues.filter(i => i.status === "REPORTED").length;

    document.getElementById("progressIssues").textContent =
        issues.filter(i => i.status === "IN_PROGRESS").length;

    document.getElementById("closedIssues").textContent =
        issues.filter(i => i.status === "CLOSED").length;
}


// ===============================
// VIEW ISSUE
// ===============================

async function viewIssue(issueId) {

    try {

        currentIssueId = issueId;

        const response = await fetch(
            `${API_URL}/api/v1/issues/${issueId}`,
            {
                headers: {
                    "Authorization": `Bearer ${TOKEN}`
                }
            }
        );

        if (!response.ok) {
            throw new Error("Unable to load issue");
        }

        const issue = await response.json();


        document.getElementById("modalIssueKey").textContent =
            issue.issue_key || "-";

        document.getElementById("modalTitle").textContent =
            issue.title || "-";

        document.getElementById("modalDescription").textContent =
            issue.description || "-";

        document.getElementById("modalReproduction").textContent =
            issue.reproduction_steps || "-";

        document.getElementById("modalSeverity").textContent =
            issue.severity || "-";

        document.getElementById("modalPriority").textContent =
            issue.priority || "-";

        document.getElementById("modalStatus").textContent =
            issue.status || "-";

        document.getElementById("modalProject").textContent =
            issue.project_id || "-";

        document.getElementById("modalAssignee").textContent =
            issue.assignee_id || "Unassigned";

        document.getElementById("modalEnvironment").textContent =
            issue.environment_details || "-";

        document.getElementById("modalEffort").textContent =
            issue.estimated_effort || "-";

        document.getElementById("modalStatusSelect").value =
            issue.status;

        document.getElementById("statusMessage").textContent = "";

        loadDevelopers();

        // Load comments
        loadComments(issueId);

        // Load activity
        loadActivity(issueId);


        const modal = document.getElementById("issueModal");

        modal.classList.remove("hidden");
        modal.classList.add("flex");

    } catch (error) {

        console.error(error);

        alert("Unable to load issue details.");

    }
}
async function loadComments(issueId) {

    try {

        const response = await fetch(
            `${API_URL}/api/v1/comments/${issueId}`,
            {
                headers: {
                    "Authorization": `Bearer ${TOKEN}`
                }
            }
        );

        if (!response.ok) {
            throw new Error("Unable to load comments");
        }

        const comments = await response.json();

        const commentsList = document.getElementById("commentsList");

        if (comments.length === 0) {
            commentsList.innerHTML =
                '<p class="text-gray-500">No comments yet.</p>';
            return;
        }

        commentsList.innerHTML = comments.map(comment => `
            <div class="border rounded-lg p-3 bg-gray-50">
                <p class="text-gray-800">${comment.comment}</p>
                <p class="text-xs text-gray-500 mt-1">
                    User ${comment.user_id} • ${new Date(comment.created_at).toLocaleString()}
                </p>
            </div>
        `).join("");

    } catch (error) {

        console.error("Comments error:", error);

    }
}

async function loadActivity(issueId) {

    try {

        const response = await fetch(
            `${API_URL}/api/v1/activity/${issueId}`,
            {
                headers: {
                    "Authorization": `Bearer ${TOKEN}`
                }
            }
        );

        if (!response.ok) {
            throw new Error("Unable to load activity");
        }

        const activities = await response.json();

        const activityList = document.getElementById("activityList");

        if (activities.length === 0) {
            activityList.innerHTML =
                '<p class="text-gray-500">No activity yet.</p>';
            return;
        }

        activityList.innerHTML = activities.map(activity => `
            <div class="border-l-4 border-blue-500 pl-3 py-2">
                <p class="font-medium">${activity.action}</p>
                <p class="text-sm text-gray-600">
                    ${activity.details || ""}
                </p>
                <p class="text-xs text-gray-500 mt-1">
                    User ${activity.user_id} • ${new Date(activity.created_at).toLocaleString()}
                </p>
            </div>
        `).join("");

    } catch (error) {

        console.error("Activity error:", error);

    }
}
// ===============================
// CLOSE MODAL
// ===============================

function closeIssueModal() {

    const modal = document.getElementById("issueModal");

    modal.classList.add("hidden");

    modal.classList.remove("flex");

    currentIssueId = null;
}


// ===============================
// CHANGE STATUS
// ===============================
async function changeIssueStatus() {

    if (!currentIssueId) {
        return;
    }

    const newStatus =
        document.getElementById("modalStatusSelect").value;

    const message =
        document.getElementById("statusMessage");

    try {

        const response = await fetch(
            `${API_URL}/api/v1/issues/${currentIssueId}/status?status=${encodeURIComponent(newStatus)}`,
            {
                method: "PATCH",

                headers: {
                    "Authorization": `Bearer ${TOKEN}`
                }
            }
        );

        const data = await response.json();

        if (!response.ok) {

            message.textContent =
                typeof data.detail === "string"
                    ? data.detail
                    : "Status update failed";

            message.className =
                "mt-3 text-red-600";

            return;
        }

        message.textContent =
            "Status updated successfully!";

        message.className =
            "mt-3 text-green-600";

        document.getElementById("modalStatus").textContent =
            newStatus;

        await loadIssues();

    } catch (error) {

        console.error(error);

        message.textContent =
            "Something went wrong.";

        message.className =
            "mt-3 text-red-600";
    }
}
// ===============================
// SEARCH
// ===============================

document.getElementById("searchInput").addEventListener(
    "input",
    function () {

        const searchText =
            this.value.toLowerCase();

        const rows =
            document.querySelectorAll("#issueTable tr");


        rows.forEach(row => {

            const text =
                row.textContent.toLowerCase();

            row.style.display =
                text.includes(searchText)
                    ? ""
                    : "none";
        });

    }
);


// ===============================
// CREATE ISSUE
// ===============================

document.getElementById("issueForm").addEventListener(
    "submit",
    async function (event) {

        event.preventDefault();


        const title =
            document.getElementById("issueTitle").value;

        const description =
            document.getElementById("issueDescription").value;

        const reproductionSteps =
            document.getElementById("reproductionSteps").value;

        const severity =
            document.getElementById("severity").value;

        const priority =
            document.getElementById("priority").value;

        const projectId =
            document.getElementById("projectId").value;

        const categoryId =
            document.getElementById("categoryId").value;

        const environmentDetails =
            document.getElementById("environmentDetails").value;

        const estimatedEffort =
            document.getElementById("estimatedEffort").value;


        const params = new URLSearchParams({

            title: title,

            description: description,

            reproduction_steps: reproductionSteps,

            severity: severity,

            priority: priority,

            project_id: projectId,

            category_id: categoryId,

            environment_details: environmentDetails,

            estimated_effort: estimatedEffort

        });


        try {

            const response = await fetch(
                `${API_URL}/api/v1/issues/?${params.toString()}`,
                {
                    method: "POST",

                    headers: {
                        "Authorization":
                            `Bearer ${TOKEN}`
                    }
                }
            );


            const data = await response.json();


            const message =
                document.getElementById("issueMessage");


            if (!response.ok) {

                message.textContent =
                    data.detail || "Failed to create issue";

                message.className =
                    "mt-4 text-red-600";

                return;
            }


            message.textContent =
                `Issue ${data.issue_key} created successfully!`;

            message.className =
                "mt-4 text-green-600";


            document.getElementById("issueForm").reset();


            document.getElementById("projectId").value = 6;

            document.getElementById("categoryId").value = 1;

            document.getElementById("estimatedEffort").value = 1;


            await loadIssues();

        } catch (error) {

            console.error(error);

            document.getElementById("issueMessage").textContent =
                "Server connection error.";

        }

    }
);


// ===============================
// DUPLICATE CHECK
// ===============================

document.getElementById("issueTitle").addEventListener(
    "blur",
    async function () {

        const title = this.value.trim();

        const projectId =
            document.getElementById("projectId").value;

        const warning =
            document.getElementById("duplicateWarning");


        if (!title) {

            warning.classList.add("hidden");

            return;
        }


        try {

            const params = new URLSearchParams({

                title: title,

                project_id: projectId

            });


            const response = await fetch(
                `${API_URL}/api/v1/issues/check-duplicates?${params.toString()}`,
                {
                    method: "POST",

                    headers: {
                        "Authorization":
                            `Bearer ${TOKEN}`
                    }
                }
            );


            const data = await response.json();


            if (data.is_duplicate) {

                warning.innerHTML = `
                    <strong>⚠ Possible Duplicate Issue</strong>
                    <br>
                    Similar issue already exists.
                `;

                warning.classList.remove("hidden");

            } else {

                warning.classList.add("hidden");

            }

        } catch (error) {

            console.error(error);

        }

    }
);


// ===============================
// INITIAL LOAD
// ===============================
// ===============================
// LOAD DEVELOPERS
// ===============================

async function loadDevelopers() {

    const select =
        document.getElementById("developerSelect");

    try {

        const response = await fetch(
            `${API_URL}/api/v1/auth/users`,
            {
                headers: {
                    "Authorization": `Bearer ${TOKEN}`
                }
            }
        );

        if (!response.ok) {
            throw new Error("Failed to load users");
        }

        const users = await response.json();

        select.innerHTML =
            `<option value="">Select Developer</option>`;

        users
            .filter(user => user.role === "DEVELOPER")
            .forEach(user => {

                const option =
                    document.createElement("option");

                option.value = user.id;

                option.textContent =
                    `${user.username} (ID: ${user.id})`;

                select.appendChild(option);
            });

    } catch (error) {

        console.error(error);

        select.innerHTML =
            `<option value="">Unable to load developers</option>`;
    }
}


// ===============================
// ASSIGN ISSUE
// ===============================

async function assignIssue() {

    if (!currentIssueId) {
        return;
    }

    const developerId =
        document.getElementById("developerSelect").value;

    const message =
        document.getElementById("assignMessage");

    if (!developerId) {

        message.textContent =
            "Please select a developer.";

        message.className =
            "mt-3 text-red-600";

        return;
    }

    try {

        const response = await fetch(
            `${API_URL}/api/v1/issues/${currentIssueId}/assign?assignee_id=${developerId}`,
            {
                method: "PATCH",

                headers: {
                    "Authorization":
                        `Bearer ${TOKEN}`
                }
            }
        );

        const data = await response.json();

        if (!response.ok) {

            message.textContent =
                typeof data.detail === "string"
                    ? data.detail
                    : "Assignment failed";

            message.className =
                "mt-3 text-red-600";

            return;
        }

        message.textContent =
            "Issue assigned successfully!";

        message.className =
            "mt-3 text-green-600";

        document.getElementById("modalAssignee").textContent =
            developerId;

        await loadIssues();

    } catch (error) {

        console.error(error);

        message.textContent =
            "Something went wrong.";

        message.className =
            "mt-3 text-red-600";
    }
}
loadIssues();

async function uploadAttachment() {
    if (!currentIssueId) {
        return;
    }

    const input = document.getElementById("attachmentInput");
    const message = document.getElementById("attachmentMessage");

    if (!input.files.length) {
        message.textContent = "Please select a file.";
        message.className = "mt-3 text-sm text-red-600";
        return;
    }

    const file = input.files[0];

    const formData = new FormData();
    formData.append("file", file);

    try {
        const response = await fetch(
            `${API_URL}/api/v1/attachments/${currentIssueId}`,
            {
                method: "POST",
                headers: {
                    "Authorization": `Bearer ${TOKEN}`
                },
                body: formData
            }
        );

        const data = await response.json();

        if (!response.ok) {
            message.textContent =
                typeof data.detail === "string"
                    ? data.detail
                    : "Failed to upload attachment.";

            message.className = "mt-3 text-sm text-red-600";
            return;
        }

        message.textContent =
            `Attachment uploaded successfully: ${data.filename}`;

        message.className = "mt-3 text-sm text-green-600";

        input.value = "";

        await loadActivity(currentIssueId);

    } catch (error) {
        console.error(error);

        message.textContent = "Something went wrong while uploading.";
        message.className = "mt-3 text-sm text-red-600";
    }
}
async function loadSprintAndBacklog() {
    try {
        // Load Sprints
        const sprintResponse = await fetch(
            `${API_URL}/api/v1/sprints/?project_id=6`,
            {
                headers: {
                    "Authorization": `Bearer ${TOKEN}`
                }
            }
        );

        const sprints = await sprintResponse.json();
        const currentSprint = sprints[0];

        // Show Sprint
        if (!currentSprint) {
            document.getElementById("sprintName").textContent = "No Sprint";
            document.getElementById("sprintGoal").textContent =
                "No sprint found.";
            document.getElementById("sprintStatus").textContent = "-";
            document.getElementById("sprintIssues").innerHTML =
                '<p class="text-sm text-slate-400">No sprint issues.</p>';
        } else {

            document.getElementById("sprintName").textContent =
                currentSprint.name;

            document.getElementById("sprintGoal").textContent =
                currentSprint.goal || "No sprint goal";

            document.getElementById("sprintStatus").textContent =
                currentSprint.status;


            // Load all issues
            const issuesResponse = await fetch(
                `${API_URL}/api/v1/issues/`,
                {
                    headers: {
                        "Authorization": `Bearer ${TOKEN}`
                    }
                }
            );

            const issues = await issuesResponse.json();

            // Only sprint issues
           const sprintIssues = issues.filter(
                 issue => Number(issue.sprint_id) === Number(currentSprint.id)
            );

            const sprintBox =
                document.getElementById("sprintIssues");

            if (!sprintIssues.length) {

                sprintBox.innerHTML =
                    '<p class="text-sm text-slate-400">No issues in this sprint.</p>';

            } else {

                sprintBox.innerHTML = sprintIssues.map(issue => `
                    <div class="flex items-center justify-between bg-slate-50 border border-slate-200 rounded-xl px-4 py-3">

                        <div>
                            <p class="font-semibold text-indigo-600">
                                ${issue.issue_key}
                            </p>

                            <p class="text-sm text-slate-700">
                                ${issue.title}
                            </p>
                        </div>

                        <span class="text-xs px-2 py-1 rounded-full bg-slate-200">
                            ${issue.status}
                        </span>

                    </div>
                `).join("");
            }
        }


        // Load Backlog
        const backlogResponse = await fetch(
            `${API_URL}/api/v1/sprints/backlog/6`,
            {
                headers: {
                    "Authorization": `Bearer ${TOKEN}`
                }
            }
        );

        const backlog = await backlogResponse.json();

        const backlogBox =
            document.getElementById("backlogList");

        if (!backlog.length) {

            backlogBox.innerHTML =
                '<p class="text-sm text-slate-400">Backlog is empty.</p>';

        } else {

            backlogBox.innerHTML = backlog.map(issue => `
                <div class="border border-slate-200 rounded-xl p-4">

                    <div class="flex items-start justify-between gap-3">

                        <div>
                            <p class="font-semibold text-indigo-600">
                                ${issue.issue_key}
                            </p>

                            <p class="text-sm font-medium text-slate-800 mt-1">
                                ${issue.title}
                            </p>
                        </div>

                        <span class="text-xs bg-amber-100 text-amber-700 px-2 py-1 rounded-full">
                            ${issue.priority}
                        </span>

                    </div>

                    <p class="text-xs text-slate-500 mt-2">
                        ${issue.severity} · ${issue.status}
                    </p>

                </div>
            `).join("");
        }

    } catch (error) {
        console.error("Sprint/Backlog error:", error);
    }
}

async function loadStatusSummary() {
    try {
        const response = await fetch(
            `${API_URL}/api/v1/issues/`,
            {
                headers: {
                    "Authorization": `Bearer ${TOKEN}`
                }
            }
        );

        const issues = await response.json();

        const reported = issues.filter(
            issue => issue.status === "REPORTED"
        ).length;

        const inProgress = issues.filter(
            issue => issue.status === "IN_PROGRESS"
        ).length;

        const resolved = issues.filter(
            issue => issue.status === "RESOLVED"
        ).length;

        const closed = issues.filter(
            issue => issue.status === "CLOSED"
        ).length;

        document.getElementById("summaryReported").textContent = reported;
        document.getElementById("summaryProgress").textContent = inProgress;
        document.getElementById("summaryResolved").textContent = resolved;
        document.getElementById("summaryClosed").textContent = closed;

    } catch (error) {
        console.error("Status summary error:", error);
    }
}
loadStatusSummary();
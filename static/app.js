const API_BASE = "http://localhost:8000";

async function loadMembers(groupName) {

    const response = await fetch(
        `${API_BASE}/groups/${groupName}/members`
    );

    const data = await response.json();

    let listId =
        groupName === "Python-Test-Group-1"
            ? "group1Members"
            : "group2Members";

    const list = document.getElementById(listId);

    list.innerHTML = "";

    data.members.forEach(member => {

        const li = document.createElement("li");

        li.textContent = member;

        list.appendChild(li);
    });
}

async function addUser(groupName, inputId) {

    const email =
        document.getElementById(inputId).value;

    const response = await fetch(
        `${API_BASE}/groups/${groupName}/users/${email}`,
        {
            method: "POST"
        }
    );

    const data = await response.json();

    alert(data.message || JSON.stringify(data));

    loadMembers(groupName);
}

async function removeUser(groupName, inputId) {

    const email =
        document.getElementById(inputId).value;

    const response = await fetch(
        `${API_BASE}/groups/${groupName}/users/${email}`,
        {
            method: "DELETE"
        }
    );

    const data = await response.json();

    alert(data.message || JSON.stringify(data));

    loadMembers(groupName);
}

async function syncGroups() {

    const response = await fetch(
        `${API_BASE}/groups/sync?source_group=Python-Test-Group-1&target_group=Python-Test-Group-2`,
        {
            method: "POST"
        }
    );

    const data = await response.json();

    alert(
        `Added: ${data.added}\nRemoved: ${data.removed}`
    );

    loadMembers("Python-Test-Group-2");
}
HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        {css}
    </style>
</head>
<body>
    <div class="header">
        <h1>{title} <span class="status-badge">{status}</span></h1>
        <p>{timestamp}</p>
    </div>

    <div class="dashboard">
        <div class="stat-card">
            <small>Processed Items</small>
            <div id="statCount">{count}</div>
        </div>
        <div class="stat-card">
            <small>Total Volume</small>
            <div id="insVolume">N/A</div>
        </div>
        <div class="stat-card">
            <small>Average Size</small>
            <div id="insAvgSize">N/A</div>
        </div>
        <div class="stat-card">
            <small>Alerts</small>
            <div id="insAlerts">0 Files</div>
        </div>
    </div>

    <div class="controls">
        <div class="search-row">
            <input type="text" id="searchInput" class="search-box" placeholder="Filter..." oninput="filterData()">
            <button class="reset-btn" onclick="resetView()">RESET</button>
        </div>
        <div class="toggle-row">
            <span class="toggle-label">Toggle Columns:</span>
            <button class="toggle-btn active" onclick="toggleColumn(0, this)">Action</button>
            <button class="toggle-btn active" onclick="toggleColumn(1, this)">Source</button>
            <button class="toggle-btn active" onclick="toggleColumn(2, this)">Destination</button>
            <button class="toggle-btn active" onclick="toggleColumn(3, this)">Size</button>
            <button class="toggle-btn active" onclick="toggleColumn(4, this)">Date</button>
            <button class="toggle-btn active" onclick="toggleColumn(5, this)">Tier</button>
            <button class="toggle-btn active" onclick="toggleColumn(6, this)">Error</button>
        </div>
    </div>

    <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th id="th-0" onclick="applySort(0)">Action</th>
                    <th id="th-1" onclick="applySort(1)">Source</th>
                    <th id="th-2" onclick="applySort(2)">Destination</th>
                    <th id="th-3" onclick="applySort(3)">Size</th>
                    <th id="th-4" onclick="applySort(4)">Date</th>
                    <th id="th-5" onclick="applySort(5)">Tier</th>
                    <th id="th-6" onclick="applySort(6)">Error</th>
                </tr>
            </thead>
            <tbody id="tableBody"></tbody>
        </table>
    </div>

    <script>
        {js}
    </script>
</body>
</html>"""
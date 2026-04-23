<?php
/**
 * Stockholm Quant - SoftBot PHP Bridge
 * This file serves as the entry point for /softbot on your website.
 * It embeds the Streamlit dashboard which runs on a internal port.
 */

// Configuration
$streamlit_url = "http://127.0.0.1:8501"; // Change this if your Streamlit runs elsewhere
$page_title = "Stockholm Quant | SoftBot";

?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php echo $page_title; ?></title>
    <style>
        body, html {
            margin: 0;
            padding: 0;
            height: 100%;
            width: 100%;
            overflow: hidden;
            background-color: #020617; /* Matches the dashboard OLED background */
        }
        iframe {
            border: none;
            width: 100%;
            height: 100%;
        }
        .loading-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: #020617;
            display: flex;
            justify-content: center;
            align-items: center;
            color: #22C55E;
            font-family: 'Fira Code', monospace;
            z-index: 9999;
            transition: opacity 0.5s ease;
        }
    </style>
</head>
<body>
    <div id="loader" class="loading-overlay">
        <div>Initializing Stockholm Quant Intelligence...</div>
    </div>

    <iframe 
        src="<?php echo $streamlit_url; ?>?embed=true" 
        onload="document.getElementById('loader').style.opacity='0'; setTimeout(() => document.getElementById('loader').style.display='none', 500);">
    </iframe>
</body>
</html>

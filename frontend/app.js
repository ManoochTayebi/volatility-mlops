// API is served by the same FastAPI host as the frontend static pages.
const API_BASE_URL = window.location.origin;
const CHART_THEME = {
  historical: '#0057ff',
  predicted: '#ff4d00',
  portfolio: '#00b894',
  text: '#171717',
  muted: '#4f4f4f',
  grid: 'rgba(23, 23, 23, 0.16)',
  paper: '#fffdf6',
  plot: '#fff5d8',
  legend: 'rgba(255, 253, 246, 0.95)'
};

async function loadAsset() {
  const params = new URLSearchParams(window.location.search);
  const asset = params.get("asset");
  const days = document.getElementById("days").value;
  const historicalPeriod = document.getElementById("historical-period") ? document.getElementById("historical-period").value : "30";

  if (!asset || !days || isNaN(days) || days < 1 || days > 7) {
    alert("Please provide a valid asset and days (1-7).");
    return;
  }

  try {
    // Clear the plot div and show loading
    const plotDiv = document.getElementById("plot");
    plotDiv.innerHTML = "<div class='text-center'><div class='spinner-border' role='status'><span class='visually-hidden'>Loading...</span></div><p>Loading predictions...</p></div>";

    const res = await fetch(`${API_BASE_URL}/api/asset_volatility?asset=${asset}&days=${days}&historical_period=${historicalPeriod}`);
    const data = await res.json();

    if (data.status === 'error') {
      throw new Error(data.error);
    }

    if (!data.historical_dates || !data.predicted_dates) {
      throw new Error('Invalid response format from server');
    }

    const trace1 = {
      x: data.historical_dates,
      y: data.historical_vol,
      mode: "lines",
      name: "Historical Volatility",
      line: { color: CHART_THEME.historical, width: 3, shape: 'spline', smoothing: 1.05, dash: 'dashdot' },
      type: 'scatter'
    };
    
    const trace2 = {
      x: data.predicted_dates,
      y: data.predicted_vol,
      mode: "lines+markers",
      name: "Predicted Volatility",
      line: { color: CHART_THEME.predicted, width: 3, shape: 'spline', smoothing: 1.05 },
      marker: { color: CHART_THEME.predicted, size: 9, symbol: 'square' },
      fill: 'tozeroy',
      fillcolor: 'rgba(255, 77, 0, 0.16)',
      type: 'scatter'
    };

    const layout = {
      title: {
        text: `${asset} Volatility Prediction`,
        font: { size: 20, color: CHART_THEME.text }
      },
      xaxis: { 
        title: 'Date',
        titlefont: { size: 14, color: CHART_THEME.text },
        tickfont: { color: CHART_THEME.muted },
        gridcolor: CHART_THEME.grid,
        linecolor: CHART_THEME.grid,
        showspikes: true,
        spikesnap: 'data',
        spikemode: 'across',
        spikethickness: 2,
        spikecolor: CHART_THEME.text,
        spikedash: 'solid'
      },
      yaxis: { 
        title: 'Volatility',
        titlefont: { size: 14, color: CHART_THEME.text },
        tickfont: { color: CHART_THEME.muted },
        gridcolor: CHART_THEME.grid,
        linecolor: CHART_THEME.grid
      },
      showlegend: true,
      height: 500,
      margin: { l: 60, r: 60, t: 80, b: 60 },
      paper_bgcolor: CHART_THEME.paper,
      plot_bgcolor: CHART_THEME.plot,
      font: { color: CHART_THEME.text },
      legend: {
        font: { color: CHART_THEME.text },
        bgcolor: CHART_THEME.legend,
        bordercolor: CHART_THEME.grid,
        borderwidth: 1
      },
      hovermode: 'x unified'
    };

    const config = {
      responsive: true,
      displayModeBar: true,
      modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d'],
      displaylogo: false,
      toImageButtonOptions: {
        format: 'png',
        filename: `${asset}_volatility_prediction`,
        height: 500,
        width: 900,
        scale: 1
      }
    };

    // Clear loading and create plot
    plotDiv.innerHTML = "";
    await Plotly.newPlot("plot", [trace1, trace2], layout, config);
    
  } catch (error) {
    console.error('Error loading asset data:', error);
    document.getElementById("plot").innerHTML = `<div class='alert alert-danger'>Error: ${error.message}</div>`;
  }
}

async function loadPortfolio(assets, days) {
  return loadPortfolioWithHistory(assets, days, 30); // Default to 30 days for backward compatibility
}

async function loadPortfolioWithHistory(assets, days, historicalPeriod = 30) {
  if (!assets || !Array.isArray(assets) || assets.length === 0 || !days || isNaN(days) || days < 1 || days > 7) {
    alert("Please provide valid assets and days (1-7).");
    return;
  }

  try {
    // Show loading indicator
    const plotsDiv = document.getElementById("plots");
    plotsDiv.innerHTML = "<div class='text-center'><div class='spinner-border' role='status'><span class='visually-hidden'>Loading...</span></div><p>Loading portfolio predictions...</p></div>";

    const res = await fetch(`${API_BASE_URL}/api/portfolio_volatility`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ assets, days, historical_period: historicalPeriod })
    });
    
    const data = await res.json();

    if (data.status === 'error') {
      throw new Error(data.error);
    }

    plotsDiv.innerHTML = "";

    // Create portfolio volatility plot
    const portfolioDiv = document.createElement("div");
    portfolioDiv.classList.add("mb-4");
    portfolioDiv.style.background = "var(--bg-secondary)";
    portfolioDiv.style.borderRadius = "12px";
    portfolioDiv.style.border = "2px solid var(--accent-primary)";
    portfolioDiv.style.padding = "20px";
    portfolioDiv.style.marginBottom = "40px";
    plotsDiv.appendChild(portfolioDiv);

    // Portfolio traces - historical and predicted
    const portfolioTraces = [];
    
    // Historical portfolio volatility
    if (data.historical_dates && data.historical_portfolio_vol) {
      portfolioTraces.push({
        x: data.historical_dates,
        y: data.historical_portfolio_vol,
        mode: "lines",
        name: "Historical Portfolio Volatility",
        line: { color: CHART_THEME.historical, width: 4, shape: 'spline', smoothing: 1.05, dash: 'dashdot' },
        type: 'scatter'
      });
    }
    
    // Predicted portfolio volatility
    portfolioTraces.push({
      x: data.predicted_dates,
      y: data.portfolio_vol,
      mode: "lines+markers",
      name: "Predicted Portfolio Volatility",
      line: { color: CHART_THEME.portfolio, width: 5, shape: 'spline', smoothing: 1.05 },
      marker: { color: CHART_THEME.portfolio, size: 10, symbol: 'square' },
      fill: 'tozeroy',
      fillcolor: 'rgba(0, 184, 148, 0.14)',
      type: 'scatter'
    });

    const portfolioLayout = {
      title: {
        text: `Portfolio Volatility (${data.assets.join(', ')})`,
        font: { size: 18, color: CHART_THEME.text }
      },
      xaxis: { 
        title: 'Date',
        titlefont: { color: CHART_THEME.text },
        tickfont: { color: CHART_THEME.muted },
        gridcolor: CHART_THEME.grid,
        linecolor: CHART_THEME.grid,
        showspikes: true,
        spikesnap: 'data',
        spikemode: 'across',
        spikethickness: 2,
        spikecolor: CHART_THEME.text,
        spikedash: 'solid'
      },
      yaxis: { 
        title: 'Portfolio Volatility',
        titlefont: { color: CHART_THEME.text },
        tickfont: { color: CHART_THEME.muted },
        gridcolor: CHART_THEME.grid,
        linecolor: CHART_THEME.grid
      },
      showlegend: true,
      height: 400,
      margin: { l: 60, r: 60, t: 80, b: 60 },
      paper_bgcolor: CHART_THEME.paper,
      plot_bgcolor: CHART_THEME.plot,
      font: { color: CHART_THEME.text },
      legend: {
        font: { color: CHART_THEME.text },
        bgcolor: CHART_THEME.legend,
        bordercolor: CHART_THEME.grid,
        borderwidth: 1
      },
      hovermode: 'x unified'
    };

    const config = {
      responsive: true,
      displayModeBar: true
    };

    Plotly.newPlot(portfolioDiv, portfolioTraces, portfolioLayout, config);

    // Add separator and title for individual assets
    const separatorDiv = document.createElement("div");
    separatorDiv.innerHTML = `
      <div style="text-align: center; margin: 40px 0 30px 0;">
        <h4 style="color: var(--accent-primary); margin-bottom: 10px;">Individual Asset Analysis</h4>
        <div style="height: 2px; background: linear-gradient(90deg, transparent, var(--accent-primary), transparent); margin: 0 auto; width: 60%;"></div>
      </div>
    `;
    plotsDiv.appendChild(separatorDiv);

    // Create individual asset plots
    for (const asset of data.assets) {
      const div = document.createElement("div");
      div.classList.add("mb-4");
      div.style.background = "var(--bg-tertiary)";
      div.style.borderRadius = "12px";
      div.style.border = "1px solid var(--border-color)";
      div.style.padding = "20px";
      div.style.marginBottom = "30px";
      plotsDiv.appendChild(div);

      const assetTraces = [];
      
      // Historical data for this asset
      if (data.historical_dates && data.individual_historical && data.individual_historical[asset]) {
        assetTraces.push({
          x: data.historical_dates,
          y: data.individual_historical[asset],
          mode: "lines",
          name: `${asset} Historical Volatility`,
          line: { color: CHART_THEME.historical, width: 3, shape: 'spline', smoothing: 1.05, dash: 'dashdot' },
          type: 'scatter'
        });
      }
      
      // Predicted data for this asset
      assetTraces.push({
        x: data.predicted_dates,
        y: data.individual_predictions[asset],
        mode: "lines+markers",
        name: `${asset} Predicted Volatility`,
        line: { color: CHART_THEME.predicted, width: 3, shape: 'spline', smoothing: 1.05 },
        marker: { color: CHART_THEME.predicted, size: 7, symbol: 'square' },
        fill: 'tozeroy',
        fillcolor: 'rgba(255, 77, 0, 0.14)',
        type: 'scatter'
      });

      const assetLayout = {
        title: {
          text: `${asset} Individual Volatility`,
          font: { size: 16, color: CHART_THEME.text }
        },
        xaxis: { 
          title: 'Date',
          color: CHART_THEME.text,
          gridcolor: CHART_THEME.grid,
          zerolinecolor: CHART_THEME.grid,
          showspikes: true,
          spikesnap: 'data',
          spikemode: 'across',
          spikethickness: 2,
          spikecolor: CHART_THEME.text,
          spikedash: 'solid'
        },
        yaxis: { 
          title: 'Volatility',
          color: CHART_THEME.text,
          gridcolor: CHART_THEME.grid,
          zerolinecolor: CHART_THEME.grid
        },
        showlegend: true,
        height: 350,
        margin: { l: 60, r: 60, t: 60, b: 60 },
        paper_bgcolor: CHART_THEME.paper,
        plot_bgcolor: CHART_THEME.plot,
        font: { color: CHART_THEME.text },
        legend: {
          font: { color: CHART_THEME.text },
          bgcolor: CHART_THEME.legend,
          bordercolor: CHART_THEME.grid,
          borderwidth: 1
        },
        hovermode: 'x unified'
      };

      Plotly.newPlot(div, assetTraces, assetLayout, config);
    }

  } catch (error) {
    console.error('Error loading portfolio data:', error);
    document.getElementById("plots").innerHTML = `<div class='alert alert-danger'>Error: ${error.message}</div>`;
  }
}

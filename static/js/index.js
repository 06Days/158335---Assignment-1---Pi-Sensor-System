// Default timeframe filter
let currentLimit = 60;

document.getElementById('timeRangeGroup').addEventListener('change', (click)=>{
  if (click.target.name ==='timeRange'){
    currentLimit = click.target.value;
    loadHistory();
  }
});

// Canvas code
const tempcanvas=document.getElementById('temperatureChart').getContext('2d');
const humidcanvas=document.getElementById('humidityChart').getContext('2d');
const pressurecanvas=document.getElementById('pressureChart').getContext('2d');

const tempchart = new Chart(tempcanvas, {
  type: 'scatter',
  data: {
    labels: [],
    datasets: [{
      label: 'Temperature (°C)',
      borderColor:'black',
      backgroundColor: 'rgba(255,0,0,0.3)',
      data: [],
      }
    ]
  },
  options: {
    animation: false,
    scales: {
      x: {
        type: 'time',
        time: {unit: 'minute'},
        ticks:{
          // invasive but hopefully will work
          callback: function(value, index, values){
            return new Date(value).toLocaleTimeString([],{
              hour:'2-digit',
              minute:'2-digit'
          });
          }
        },
        displayFormats:{
          minute: 'HH:mm'
        },
        title: {display: true, text: 'Time'}
      },
      y: {beginAtZero: false}
    },
    plugins:{
      annotation:{
        annotations:{
          maxLine:{
            type:'line',
            yMin:0,
            yMax:0,
            borderColor:'red',
            borderWidth:2,
            borderDash:[6,6],
            label:{
              display:true,
              content:'High',
              position:'end'
            }
          },
          minLine:{
            type:'line',
            yMin:0,
            yMax:0,
            borderColor:'blue',
            borderWidth:2,
            borderDash:[6,6],
            label:{
              display:true,
              content:'Low',
              position:'end'
            }
          }
        }
      }
    }
  }});
const humidchart = new Chart(humidcanvas, {
  type: 'scatter',
  data: {
    labels: [],
    datasets: [{
      label: 'Humidity (%)',
      borderColor:'black',
      backgroundColor: 'rgba(0,255,0,0.3)',
      data: [],
      }
    ]
  },
  options: {
    animation: false,
    scales: {
      x: {
        type: 'time',
        time: {unit: 'minute'},
        ticks:{
          // invasive but hopefully will work
          callback: function(value, index, values){
            return new Date(value).toLocaleTimeString([],{
              hour:'2-digit',
              minute:'2-digit'
          });
          }
        },
        displayFormats:{
          minute: 'HH:mm'
        },
        title: {display: true, text: 'Time'}
      },
      y: {beginAtZero: false}
    },
    plugins:{
      annotation:{
        annotations:{
          maxLine:{
            type:'line',
            yMin:0,
            yMax:0,
            borderColor:'red',
            borderWidth:2,
            borderDash:[6,6],
            label:{
              display:true,
              content:'High',
              position:'end'
            }
          },
          minLine:{
            type:'line',
            yMin:0,
            yMax:0,
            borderColor:'blue',
            borderWidth:2,
            borderDash:[6,6],
            label:{
              display:true,
              content:'Low',
              position:'end'
            }
          }
        }
      }
    }
  }});
const pressurechart = new Chart(pressurecanvas, {
    type: 'scatter',
    data: {
      labels: [],
      datasets: [{
        label: 'Air Pressure (hPa)',
        borderColor:'black',
        backgroundColor: 'rgba(0,0,255,0.3)',
        data: [],
        }
      ]
    },
    options: {
      animation: false,
      scales: {
        x: {
          type: 'time',
          time: {unit: 'minute'},
          ticks:{
            // invasive but hopefully will work
            callback: function(value, index, values){
              return new Date(value).toLocaleTimeString([],{
                hour:'2-digit',
                minute:'2-digit'
            });
            }
          },
          displayFormats:{
            minute: 'HH:mm'
          },
          title: {display: true, text: 'Time'}
        },
        y: {beginAtZero: false}
      },
      plugins:{
        annotation:{
          annotations:{
            maxLine:{
              type:'line',
              yMin:0,
              yMax:0,
              borderColor:'red',
              borderWidth:2,
              borderDash:[6,6],
              label:{
                display:true,
                content:'High',
                position:'end'
              }
            },
            minLine:{
              type:'line',
              yMin:0,
              yMax:0,
              borderColor:'blue',
              borderWidth:2,
              borderDash:[6,6],
              label:{
                display:true,
                content:'Low',
                position:'end'
              }
            }
          }
        }
      }
    }});

async function loadHistory(){
  try{
    const result = await fetch(`/sensor/history?minutes=${currentLimit}`);
    const data = await result.json();

    if(data && data.length>0){

      const latest_data=data[data.length-1];
      document.getElementById('temperature').textContent = `${data[0].Temperature.toFixed(2)} ℃`;
      document.getElementById('humidity').textContent = `${data[0].Humidity.toFixed(2)} %`;
      document.getElementById('pressure').textContent = `${data[0].Pressure.toFixed(2)} hPa`;
      console.log("rds:", data[0].DateTime);
      const tempChartData = data.map(row => ({

        x: new Date(row.DateTime),
        y: row.Temperature
      })).filter(p =>!isNaN(p.x.getTime()));
      const humidChartData = data.map(row => ({

        x: new Date(row.DateTime),
        y: row.Humidity
      })).filter(p =>!isNaN(p.x.getTime()));
      const pressureChartData = data.map(row => ({

        x: new Date(row.DateTime),
        y: row.Pressure
      })).filter(p =>!isNaN(p.x.getTime()));

      const now= new Date();
      const past = new Date(now.getTime-currentLimit*60000);

      [tempchart, humidchart, pressurechart].forEach(chart =>{
        chart.options.scales.x.min=past;
        chart.options.scales.x.max=now;
        chart.options.scales.x.time.unit = currentLimit > 120 ? 'hour' : 'minute';
      });
      tempchart.data.datasets[0].data = tempChartData.reverse();
      humidchart.data.datasets[0].data = humidChartData.reverse();
      pressurechart.data.datasets[0].data = pressureChartData.reverse();
      updateScales();
      tempchart.update();


      humidchart.update();


      pressurechart.update();
    }
  } catch (exception){
    console.error("Could not load history! :",exception);

  }
}
async function fetchEvent(eventName){
  try {
    const response = await fetch(`/sensor/history/event?name=${encodeURIComponent(eventName)}&limit=1`);
    const data = await response.json();
    return data.length > 0 ? data[0] : null;
  } catch (exception) {
    console.error("Could NOT fetch event", exception);
    return null;
  }
}
async function updateScales(){
  const highTemp = await fetchEvent("Highest Temperature");
  const lowTemp = await fetchEvent("Lowest Temperature");
  const highPress = await fetchEvent("Highest Pressure");
  const lowPress = await fetchEvent("Lowest Pressure");
  const highHumid = await fetchEvent("Highest Humidity");
  const lowHumid = await fetchEvent("Lowest Humidity");
  // temperature y axis
  if (highTemp && lowTemp) {
      tempchart.options.scales.y.min = Math.floor(lowTemp.Temperature);
      tempchart.options.scales.y.max = Math.ceil(highTemp.Temperature);
      tempchart.options.plugins.annotation.annotations.maxLine.yMin = highTemp.Temperature;
      tempchart.options.plugins.annotation.annotations.maxLine.yMax = highTemp.Temperature;
      tempchart.options.plugins.annotation.annotations.minLine.yMin = lowTemp.Temperature;
      tempchart.options.plugins.annotation.annotations.minLine.yMax = lowTemp.Temperature;
      tempchart.update('none');
  }
  // humidity y axis
  if (highHumid && lowHumid) {
      humidchart.options.scales.y.min = Math.floor(lowHumid.Humidity);
      humidchart.options.scales.y.max = Math.ceil(highHumid.Humidity);
      humidchart.options.plugins.annotation.annotations.maxLine.yMin = highHumid.Humidity;
      humidchart.options.plugins.annotation.annotations.maxLine.yMax = highHumid.Humidity;
      humidchart.options.plugins.annotation.annotations.minLine.yMin = lowHumid.Humidity;
      humidchart.options.plugins.annotation.annotations.minLine.yMax = lowHumid.Humidity;
      humidchart.update('none');

  }
  // air pressure y axis
  if (highPress && lowPress) {
      pressurechart.options.scales.y.min = Math.floor(lowPress.Pressure);
      pressurechart.options.scales.y.max = Math.ceil(highPress.Pressure);


      pressurechart.options.plugins.annotation.annotations.maxLine.yMin = highPress.Pressure;
      pressurechart.options.plugins.annotation.annotations.maxLine.yMax = highPress.Pressure;
      pressurechart.options.plugins.annotation.annotations.minLine.yMin = lowPress.Pressure;
      pressurechart.options.plugins.annotation.annotations.minLine.yMax = lowPress.Pressure;
      pressurechart.update('none');
  }
}


async function updateAnalysis(){
  try {
    const result = await fetch('/sensor/analysis');
    const analysis = await result.json();
    const metrics= ['temp', 'humid', 'press'];

    metrics.forEach(metric =>{
      const data= analysis[metric]
      const badge= document.getElementById(`${metric}Trend`);
      const predictionBadge = document.getElementById(`${metric}Prediction`);

      badge.textContent = data.trend;
      if (data.trend === 'Rising') badge.className = "badge bg-warning text-dark";
      else if (data.trend === 'Falling') badge.className = "badge bg-info text-dark";
      else badge.className = "badge bg-secondary";

      if (data.prediction && data.prediction < 60) {
                const msg = `<strong>Prediction:</strong> ${metric.toUpperCase()} breach in ~${data.prediction} mins.`;
                showDismissibleAlert(`pred-${metric}`, msg, 'warning');
      }
      if (data.spike) {
                const msg = `<strong>Caution:</strong> Sudden ${metric.toUpperCase()} spike detected!`;
                showDismissibleAlert(`spike-${metric}`, msg, 'danger');
      }
    });
  }catch (exception){
    console.error("Could not fetch analysis", exception);
  }
}

function showDismissibleAlert(id, message, type) {
    if (document.getElementById(id)) return; // If there already is an alert of that nature, dont get rid of it
    const container = document.getElementById('alertContainer');
    const html = `
        <div class="alert alert-${type} alert-dismissible fade show shadow-sm" role="alert" id="${id}">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>`;
    container.insertAdjacentHTML('beforeend', html);
}

// settings sliders
// Initialize Sliders
let tempSlider, humidSlider, pressureSlider;

async function initSliders() {
    try {
        // "handshake" the backend for the settings that should be saved in system.conf
        const response = await fetch('/sensor/settings');
        const config = await response.json();
        // load from the server
        tempSlider = document.getElementById('tempSlider');
        noUiSlider.create(tempSlider, {
            start: [config.temp_low_thres, config.temp_high_thres], // Loaded from server!
            connect: true,
            range: { 'min': -30, 'max': 100 },
            step: 0.5
        });
        humidSlider = document.getElementById('humidSlider');
        noUiSlider.create(humidSlider, {
            start: [config.humid_low_thres, config.humid_high_thres],
            connect: true,
            range: { 'min': 0, 'max': 100 },
            step: 1
        });
        pressureSlider = document.getElementById('pressSlider');
        noUiSlider.create(pressSlider, {
            start: [config.press_low_thres, config.press_high_thres],
            connect: true,
            range: { 'min': 260, 'max': 1260 },
            step: 1
        });

        // live updates of the small-tagged range text
        tempSlider.noUiSlider.on('update', (values) => {
            document.getElementById('tempRangeText').innerText = `${values[0]}°C - ${values[1]}°C`;
        });
        humidSlider.noUiSlider.on('update', (values) => {
            document.getElementById('humidRangeText').innerText = `${values[0]}% - ${values[1]}%`;
        });
        pressSlider.noUiSlider.on('update', (values) => {
            document.getElementById('pressRangeText').innerText = `${Math.round(values[0])} - ${Math.round(values[1])} hPa`;
        });
        
        // spike amounts
        document.getElementById('temp_spike_amount').value = config.temp_spike_amount;
        document.getElementById('humid_spike_amount').value = config.humid_spike_amount;
        document.getElementById('press_spike_amount').value = config.press_spike_amount;

    } catch (error) {
        console.error("Failed to load slider config:", error);
    }
}




window.onload = () => {
  initSliders();
setTimeout(() => {
  loadHistory();
  setInterval(loadHistory, 1000);
}, 100);
  setInterval(updateAnalysis, 2000);
};

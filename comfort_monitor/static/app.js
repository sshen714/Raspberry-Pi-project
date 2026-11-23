/* Vue 使用 [[ ]]，避免與 Flask Jinja 的 {{ }} 衝突。 */
const {createApp} = Vue;
createApp({
  delimiters:['[[',']]'],
  data(){return {state:{stale:true},networkError:'',actionError:'',historyError:'',busy:false,changing:false,now:Date.now(),hours:24,metric:'temperature',points:[],stats:{},rangeStart:0,rangeEnd:0,bucket:120,showRules:false,historyToken:0,lastHistory:0,timer:null,clockTimer:null};},
  computed:{
    reading(){return this.state.reading;},
    comfort(){return this.state.comfort || {};},
    outdated(){return !!(this.networkError || this.state.stale || !this.reading || this.now/1000-this.reading.ts>10);},
    displayLevel(){return this.outdated?'unknown':this.comfort.level;},
    temperatureLevel(){return ['寒冷','炎熱'].includes(this.comfort.temperature_label)?'red':this.comfort.temperature_label==='舒適'?'green':'yellow';},
    humidityLevel(){return ['乾燥','潮濕'].includes(this.comfort.humidity_label)?'red':this.comfort.humidity_label==='舒適'?'green':'yellow';},
    connectionLabel(){return this.networkError?'連線中斷':this.outdated?'資料未更新':'持續監測中';},
    dateLabel(){return new Date(this.now).toLocaleDateString('zh-TW',{month:'long',day:'numeric',weekday:'long'});},
    clockLabel(){return new Date(this.now).toLocaleTimeString('zh-TW',{hour12:false,hour:'2-digit',minute:'2-digit',second:'2-digit'});},
    heroDescription(){return this.outdated?'取得新資料後，將重新判斷環境舒適度。':this.comfort.level==='green'?'溫度與濕度恰到好處，享受自在的室內時光。':this.comfort.level==='yellow'?'環境稍有變化，可以參考右側的生活建議。':'目前環境超出舒適範圍，請留意下方提醒。';},
    chart(){
      const vals=this.points.map(p=>p[this.metric]);
      const temp=this.metric==='temperature', low=temp?20:40, high=temp?26:60;
      const min=Math.floor(Math.min(low-5,...vals)/5)*5,max=Math.ceil(Math.max(high+5,...vals)/5)*5;
      const y=v=>220-(v-min)/(max-min)*200;
      const start=this.rangeStart || this.now/1000-this.hours*3600,end=this.rangeEnd || this.now/1000;
      const x=t=>50+Math.max(0,Math.min(1,(t-start)/(end-start)))*690;
      let last=null, path='',prev=null;
      for(const p of this.points){const cmd=prev===null || p.ts-prev>this.bucket*2.5?'M':'L';last={x:x(p.ts),y:y(p[this.metric])};path+=`${cmd}${last.x.toFixed(2)},${last.y.toFixed(2)} `;prev=p.ts;}
      return {path,last,bandY:y(high),bandHeight:y(low)-y(high),ticks:Array.from({length:5},(_,i)=>{const value=min+(max-min)*i/4;return {value:Math.round(value*10)/10,y:y(value)};}),times:Array.from({length:5},(_,i)=>({x:50+i*172.5,label:this.formatTime(start+(end-start)*i/4,false),anchor:i===0?'start':i===4?'end':'middle'}))};
    }
  },
  methods:{
    value(v){return v==null || !Number.isFinite(v)?'—':v.toFixed(1);},
    formatTime(ts,seconds=true){return new Date(ts*1000).toLocaleTimeString('zh-TW',{hour12:false,hour:'2-digit',minute:'2-digit',...(seconds?{second:'2-digit'}:{})});},
    position(v,min,max){return `${Math.max(0,Math.min(100,((v??min)-min)/(max-min)*100))}%`;},
    async getJSON(url,options={}){const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),5000);try{const r=await fetch(url,{cache:'no-store',...options,signal:controller.signal});if(!r.ok)throw new Error(`HTTP ${r.status}`);return await r.json();}finally{clearTimeout(timeout);}},
    async refresh(){if(this.busy)return;this.busy=true;try{this.state=await this.getJSON('/api/latest');this.networkError='';if(Date.now()-this.lastHistory>10000)await this.loadHistory();}catch(e){this.networkError='無法取得最新資料，系統將自動重試。';}finally{this.busy=false;}},
    async loadHistory(){const token=++this.historyToken;try{const d=await this.getJSON('/api/history?hours='+this.hours);if(token!==this.historyToken)return;this.points=d.points;this.stats=d.stats;this.rangeStart=d.start;this.rangeEnd=d.end;this.bucket=d.bucket_seconds;this.historyError='';this.lastHistory=Date.now();}catch(e){if(token===this.historyToken)this.historyError='歷史資料載入失敗，將自動重試。';}},
    setHours(h){this.hours=h;this.loadHistory();},
    async changeScenario(scenario){this.changing=true;this.actionError='';try{await this.getJSON('/api/demo/scenario',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({scenario})});this.state.scenario=scenario;}catch(e){this.actionError='情境切換失敗，請確認連線後重試。';}finally{this.changing=false;}},
  },
  mounted(){document.getElementById('boot-message').remove();this.refresh();this.timer=setInterval(()=>this.refresh(),2000);this.clockTimer=setInterval(()=>this.now=Date.now(),1000);},
  beforeUnmount(){clearInterval(this.timer);clearInterval(this.clockTimer);}
}).mount('#app');

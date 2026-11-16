/* Pure DSP helpers: volume only, no time stretching or voice substitution. */
window.ZemaVoiceAudio={
 normalize(channels,targetDb=-18){
  if(!Number.isFinite(targetDb)||targetDb < -36||targetDb > -12)throw Error('Choose a valid volume target.');
  if(!channels.length||channels.length>2||!channels[0].length)throw Error('Use mono or stereo audio.');
  let peak=0,sum=0,count=0;
  for(const channel of channels){if(channel.length!==channels[0].length)throw Error('Channel lengths differ.');for(const sample of channel){if(!Number.isFinite(sample))throw Error('Invalid audio sample.');peak=Math.max(peak,Math.abs(sample));sum+=sample*sample;count++;}}
  const rms=Math.sqrt(sum/count),ceiling=10**(-1/20);
  const gain=peak<1e-7?1:Math.min(16,10**(targetDb/20)/Math.max(rms,1e-9),ceiling/peak);
  return {channels:channels.map(channel=>Float32Array.from(channel,sample=>sample*gain)),gainDb:20*Math.log10(gain),peak:peak*gain};
 },
 wav(channels,sampleRate){
  const count=channels.length,length=channels[0].length,buffer=new ArrayBuffer(44+length*count*2),view=new DataView(buffer);
  const word=(offset,text)=>{for(let i=0;i<text.length;i++)view.setUint8(offset+i,text.charCodeAt(i));};
  word(0,'RIFF');view.setUint32(4,buffer.byteLength-8,true);word(8,'WAVE');word(12,'fmt ');view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,count,true);view.setUint32(24,sampleRate,true);view.setUint32(28,sampleRate*count*2,true);view.setUint16(32,count*2,true);view.setUint16(34,16,true);word(36,'data');view.setUint32(40,length*count*2,true);
  let offset=44;for(let i=0;i<length;i++)for(const channel of channels){const sample=Math.max(-1,Math.min(1,channel[i]));view.setInt16(offset,Math.round(sample*(sample<0?32768:32767)),true);offset+=2;}
  return buffer;
 }
};

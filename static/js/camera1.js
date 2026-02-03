const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');

navigator.mediaDevices.getUserMedia({ video: true })
  .then(stream => {
    video.srcObject = stream;
    video.onloadedmetadata = () => {
      video.play();
      sendFrame(); 
    };
  })
  .catch(error => console.error("Erreur caméra:", error));

function sendFrame() {
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  canvas.toBlob(blob => {
    const formData = new FormData();
    formData.append('image', blob, 'frame.jpg');
    fetch('predict', { 
        method: 'POST', 
        body: formData 
    })
    .then(response => {
      if (!response.ok) throw new Error('Erreur réseau');
      return response.blob();
    })
    .then(blob => {
      const img = new Image();
      const url = URL.createObjectURL(blob);
      img.src = url;
      
      img.onload = () => {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);        
        URL.revokeObjectURL(url);
        setTimeout(sendFrame, 500); 
      };
    })
    .catch(error => {
      console.error("Erreur API:", error);
      setTimeout(sendFrame, 20000);
    });
  }, 'image/jpeg', 0.7);
}
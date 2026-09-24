
<h2 align="center">MCKEY - MaCros KEYboard</h2>  

<h3 align="center"> Macro USB Keyboard based on Raspberry Pi Pico  </h3>  

<p align="center">
<img src="https://raw.githubusercontent.com/GorGylka/MCKEY/refs/heads/main/readme_stuff/oled_mc_vertical_256x64.gif">
</p> 

<p align="center">
  
  <img src="https://img.shields.io/github/downloads/GorGylka/MCKEY/total.svg?color=red&style=for-the-badge&maxAge=3600"> 
  <img src="https://img.shields.io/github/stars/gorgylka/MCKEY?color=red&style=for-the-badge&maxAge=3600"> 
  <img src="https://img.shields.io/github/v/release/gorgylka/MCKEY?color=red&label=latest%20release&style=for-the-badge">   
  
</p> 


<h3 align="left">Features:</h3>  

- Detects as a standard ```USB``` keyboard  
- Works on any OS  
- ```10``` slots for macro, ```~13000``` inputs per each slot  
- ```No Driver``` required
- Easy 6 Wire assembly  
- Full control direcly from keyboard  

<h3 align="left">Assembly:</h3>  
<h3 align="left">You will need:</h2>

- Raspberry Pi Pico
- SSD1306 OLED Display, 128x64, I2C     
- PS/2 Keyboard  
  
Assemble according to this:  

<img src="https://github.com/GorGylka/MCKEY/blob/main/readme_stuff/wiring.jpg" width=60% height=60%>  

> [!NOTE]  
> To boot into service mode, bridge pin GP15 to GND before connecting to USB.  
>  This will allow you to view the firmware contents as a USB drive.  
> Also, keyboard wire colors may vary; refer to connector.

> [!CAUTION]
> Not all PS/2 keyboards tolerate 3.3V!  
> To make sure, try run keyboard from 3.3V source (GND and VCC pins)  
> If you see the Caps / Scroll / NumLock blink = keyboard has init and started  
> Next, take a multimeter and check the voltages (GND-DATA, GND-CLOCK)  
> If the floating values ​​do not exceed 3.3V, you are safe.  

<h3 align="left">Installation:</h3>  

Connect Pico while ```BOOT``` pressed, Drag and drop latest [UF2](https://github.com/GorGylka/MCKEY/releases) to pico


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
- PS/2 or USB (PS/2 compatible) Keyboard
- 2x 4.7K Ω Resistors (optional)
- Tact Button (optional)  
  
Assemble according to this:  


-  ```PICO``` GPIO2 — ```KEYBOARD``` DATA
-  ```PICO``` GPIO3 — ```KEYBOARD``` CLOCK
-  ```PICO``` 3V3 — ```KEYBOARD``` VDD
-  ```PICO``` GND — ```KEYBOARD``` GND
-  ```PICO``` GPIO4 — ```DISPLAY``` SDA
-  ```PICO``` GPIO5 — ```DISPLAY``` SCK
-  ```PICO``` 3v3 — ```DISPLAY``` VCC
-  ```PICO``` GND — ```DISPLAY``` GND
-  ```PICO``` GPIO15 — Button — RPi pico GND
-  ```PICO``` 3V3 — ```PICO``` GPIO2
-  ```PICO``` 3V3 — ```PICO``` GPIO3



<img src="https://raw.githubusercontent.com/GorGylka/MCKEY/refs/heads/main/readme_stuff/picops2.jpg" width=60% height=60%>  

<img src="https://raw.githubusercontent.com/GorGylka/MCKEY/refs/heads/main/readme_stuff/picousb.jpg" width=60% height=60%>  

<img src="https://raw.githubusercontent.com/GorGylka/MCKEY/refs/heads/main/readme_stuff/picozerops2.jpg" width=60% height=60%>  

<img src="https://raw.githubusercontent.com/GorGylka/MCKEY/refs/heads/main/readme_stuff/picozerousb.jpg" width=60% height=60%>  

> [!NOTE]  
> To boot into service mode, bridge pin GP15 to GND before connecting to USB.  
>  This will allow you to view the firmware contents as a USB drive (dump macro, e.t.c.).  
> Resistors are needed to switch USB keyboard to PS/2 mode.  
> Also, keyboard wire colors may vary; refer to connector.

> [!CAUTION]
> Not all keyboards tolerate 3.3V!  
> Not all USB keyboards have PS/2 mode.  
> In my tests, only 60% PS/2 and 30% USB keyboards are compatible.  

<h3 align="left">Installation:</h3>  

Connect Pico while ```BOOT``` pressed, Drag and drop latest [UF2](https://github.com/GorGylka/MCKEY/releases) to pico  

<h3 align="left">Usage:</h3>  

4 keys are used for control: ```HOME```, ```END```, ```PAGE_UP```, ```PAGE_DOWN```.  
Inputs from these 4 keys are not sent as keyboard presses.  
| ```HOME```— OK / Enter | ```PAGE_UP```—Up |
| ------------- | ------------- |
| ```END``` — NO / Exit | ```PAGE_DOWN```—Down |

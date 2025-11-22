// go.mod: module discord-webhook
// run: go run main.go

package main

import (
	"encoding/json"
	"crypto/md5"
	"fmt"
	"log"
	"io"
	"compress/gzip"
	"net"
	"net/url"
	"net/http"
	"net/http/httputil"
	"net/http/cookiejar"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"
        "github.com/PuerkitoBio/goquery"
        "github.com/nats-io/nats.go"
	"publisher/startup"
)

// Message is what gets sent back to the main goroutine.
type Message struct {
	Timestamp time.Time `json:"timestamp"`
	Label     string    `json:"label"`
	Value     int       `json:"value"`
	Mac	  string    `json:"mac"`
	IP	  string    `json:"ip"`
	Factor    float32   `json:"factor"`
	Reading   float32   `json:"reading"`
	Measurement float32 `json:"measurement"`
	Metric    int       `json:"metric"`
	DFI       int       `json:"dfi"`
}

// Listener periodically polls an HTTP endpoint and
// sends a message to msgCh if some condition is met.
type Listener struct {
	msgCh     chan<- Message // send-only channel to main program
	mac string
	ipAddress string
	activeInterface string
	username string
	password string
	interval time.Duration // poll interval
	requestsSinceCookieRefresh int
	cookie string
	errorCount int
}

func clientForInterface(ifName string) (*http.Client, error) {
    iface, err := net.InterfaceByName(ifName)
    if err != nil {
        return nil, fmt.Errorf("could not find interface %s: %w", ifName, err)
    }

    addrs, err := iface.Addrs()
    if err != nil {
        return nil, fmt.Errorf("could not get addresses for %s: %w", ifName, err)
    }

    var ip net.IP
    for _, addr := range addrs {
        if ipnet, ok := addr.(*net.IPNet); ok && ipnet.IP.To4() != nil {
            ip = ipnet.IP
            break
        }
    }
    if ip == nil {
        return nil, fmt.Errorf("no IPv4 address found on %s", ifName)
    }

    dialer := &net.Dialer{
        LocalAddr: &net.TCPAddr{IP: ip},
        Timeout:   3 * time.Second,
    }

    transport := &http.Transport{
        DialContext: dialer.DialContext,
    }

    jar, err := cookiejar.New(nil)
    if err != nil {
        return nil, fmt.Errorf("failed to create cookie jar: %w", err)
    }

    return &http.Client{
        Timeout: 5 * time.Second,
        Transport: transport,
	Jar: jar,
    }, nil 
}

// NewListener constructs a Listener.
// msgCh: channel to send messages on
// ipAddress: address to poll (e.g. "http://192.168.1.50/status")
// label: identifying label for this listener
func NewListener(
	msgCh chan<- Message, 
	mac string,
	ipAddress string, 
	activeInterface string,
	username string,
	password string) *Listener {
	return &Listener{
		msgCh: msgCh,
		mac: mac,
		ipAddress: ipAddress,
		activeInterface: activeInterface,
		username: username,
		password: password,
		interval:  1 * time.Second, // default poll interval
		requestsSinceCookieRefresh: 0,
		cookie: "",
		errorCount: 0,
	}
}

// Run starts the polling loop.
// Call this in a goroutine:  go listener.Run()
// All the logic for handling strange count behaviour from the iot device, and starting from 0 regardless of the current count from last session
func (l *Listener) Run() {
    var previousCount []int
    var counts []int
    previousCount = make([]int, 8)
    counts = make([]int, 8)
    for {
    	var err error
    	counts, err = l.PingDevice()
	if err != nil {
		fmt.Println(err)
		l.errorCount += 1
		continue
	}

	for i := range counts {
		switch {
		case counts[i] == previousCount[i]:
			//fmt.Printf("\n%v lane %d count has not changed: %d\n", time.Now(), i+1, counts[i])
			previousCount[i] = counts[i]

		case counts[i] == previousCount[i]+1:
			l.msgCh <- Message{
			    Timestamp:  time.Now(),
			    Label:	fmt.Sprintf("lane.%d", i+1),
			    Value:	1,
			    Mac:	l.mac,	  
			    IP:		l.ipAddress,
			    Factor:	1.0, 
			    Reading:	0.0,
			    Measurement: 0,
			    Metric:	counts[i],
			    DFI:	i,
			}
			previousCount[i] = counts[i]

		case counts[i] > previousCount[i]+10:
			// weirdness, reset both counts
			previousCount[i] = counts[i]

		case counts[i] < previousCount[i]:
			// probably integer overflow, reset both counts 
			previousCount[i] = counts[i]
		}
	}
	time.Sleep(l.interval)
    }
}

func (l *Listener) PingDevice() ([]int, error) {
    l.requestsSinceCookieRefresh += 1
    client, err := clientForInterface(l.activeInterface)
    username := l.username
    password := l.password
    var cookie string
    cookie = l.cookie
    if l.requestsSinceCookieRefresh > 20 || len(l.cookie) == 0 || l.errorCount > 3 {

	    // getting the cookie
	    l.requestsSinceCookieRefresh = 0
	    l.errorCount = 0
	    configURL := fmt.Sprintf("http://%s/config", l.ipAddress)
	    if err != nil {
		return nil, fmt.Errorf(" interface error: %v\n", err)
	    }
	    resp, err := client.Get(configURL)
	    if err != nil {
		return nil, fmt.Errorf("error while using \nusername: %s\npassword: %s\n: %v\n",username, password, err)
	    }
	    defer resp.Body.Close()

	    for _, c := range resp.Cookies() {
		fmt.Printf("received cookie: %s=%s; Domain=%s; Path=%s; Expires=%v; Secure=%v; HttpOnly=%v\n", c.Name, c.Value, c.Domain, c.Path, c.Expires, c.Secure, c.HttpOnly)
	    }

	    doc, err := goquery.NewDocumentFromReader(resp.Body)

	    if err != nil {
		return nil, fmt.Errorf("error: %v\n", err)
	    }
	    seed, exists := doc.Find("input[name='seeddata']").Attr("value")
	    if !exists {
		fmt.Printf("error: seedata not found\n")
		html, err := doc.Html()
		if err != nil {
		    return nil, fmt.Errorf("error generating HTML: %v\n", err)
		}
		return nil, fmt.Errorf("\ndoc: %s\n", html)
	    }
	    fmt.Printf("Seed value: %s\n", seed)

	    hashInput := fmt.Sprintf("%s:%s:%s", seed, username, password)
	    hash := fmt.Sprintf("%x", md5.Sum([]byte(hashInput)))

	    if len(hash) <= 1 {
		return nil, fmt.Errorf("error: %v\n", err)
	    }
	    fmt.Printf("hash: %s\n", hash)

	    simpleBody := fmt.Sprintf("seeddata=%s&authdata=%s", url.QueryEscape(seed), url.QueryEscape(hash))

	    req, _ := http.NewRequest("POST", configURL+"/index.html", strings.NewReader(simpleBody))

	    req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	    req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")
	    req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7")
	    req.Header.Set("Accept-Language", "en-US,en;q=0.9")
	    req.Header.Set("Accept-Encoding", "gzip, deflate")
	    req.Header.Set("Connection", "keep-alive")
	    req.Header.Set("Cache-Control", "no-cache")
	    req.Header.Set("Pragma", "no-cache")
	    req.Header.Set("Upgrade-Insecure-Requests", "1")

	    dump, err := httputil.DumpRequestOut(req, true)
	    if err != nil {
		fmt.Errorf("failed to dump request: %v\n", err)
	    } else {
		fmt.Printf("outgoing request:\n%s\n", string(dump))
	    }

	    resp2, err := client.Do(req)
	    if err != nil {
		return nil, fmt.Errorf("timeout when requesting cookie: %v\n", err)
	    }
	    defer resp2.Body.Close()

	    var reader io.ReadCloser
	    switch resp2.Header.Get("Content-Encoding") {
	    case "gzip":
		reader, err = gzip.NewReader(resp2.Body)
		if err != nil {
		    return nil, fmt.Errorf("failed to create gzip reader: %v\n", err)
		}
		defer reader.Close()
	    default:
		reader = resp2.Body
	    }

	    _, err = io.ReadAll(reader)
	    if err != nil {
		return nil, fmt.Errorf("failed to read body: %v\n", err)
	    }
	    //fmt.Printf("[%s] response body:\n%s\n", l.label, string(body))

	    if resp2.StatusCode != 200 {
		return nil, fmt.Errorf("Response status: %d", resp2.StatusCode)
	    }

	    for _, c := range resp2.Cookies() {
		cookie = c.Value
		fmt.Printf("Cookie: %s", cookie)
	    }
	    l.cookie = cookie
	    fmt.Printf("response cookie: %v\n", cookie)

    }

    // scrape device
    scrapeURL := fmt.Sprintf("http://%s/di_value/slot_0", l.ipAddress)
    fmt.Printf("scraping %s", scrapeURL)

    scrapeReq, err := http.NewRequest("GET", scrapeURL, nil)
    if err != nil {
	fmt.Printf("failed to create request")
	return nil, fmt.Errorf("failed to create request")
    }

    scrapeReq.Header.Set("Cookie", fmt.Sprintf("adamsessionid=%s", cookie))

    scrapeResp, err := client.Do(scrapeReq)
    if err != nil {
	fmt.Printf("request failed")
	return nil, fmt.Errorf("network error")
    }
    defer scrapeResp.Body.Close()

    body, err := io.ReadAll(scrapeResp.Body)
    if err != nil {
	fmt.Printf("failed to read response")
	return nil, fmt.Errorf("failed to read response")
    }

    var parsed struct {
        DIVal []map[string]interface{} `json:"DIVal"`
    }
    if err := json.Unmarshal(body, &parsed); err != nil {
	//fmt.Errorf("failed to parse JSON: %w", err)
	fmt.Printf("failed to parse JSON")
	return nil, fmt.Errorf("could not parse payload")
    }

    fmt.Printf("parsed data from returned json: %+v\n", parsed)

    var readings []int
    for _, val := range parsed.DIVal {
	if f, ok := val["Val"].(float64); ok {
	    readings = append(readings, int(f))
	} else {
	    fmt.Printf("unexpected type for Val: %T\n", val["Val"])
	    return nil, fmt.Errorf("type error")
	}
    }

    if len(readings) == 0 {
        return nil, fmt.Errorf("array of iot value counts was empty %v", readings)
    }
    if len(readings) < 8 {
        return nil, fmt.Errorf("array of iot value counts was had less than 8 elements %v", readings)
    }


    fmt.Printf("requests since cookie refresh: %d\n", l.requestsSinceCookieRefresh)

    return []int{readings[0], readings[1], readings[2], readings[3], readings[4], readings[5], readings[6], readings[7]}, nil
}

func trimDuration(d time.Duration) string {
	s := d.String()
	if i := strings.IndexByte(s, '.'); i != -1 {
		s = s[:i]
	}
	return s
}


func main() {


	// startup check to confirm ip of device [START]
	targetMac := "74:FE:48:5C:5D:40" // replace with real MAC

	for {
		fmt.Printf("Initializing")
		time.Sleep(1 * time.Second)
		fmt.Printf(" .")
		time.Sleep(1 * time.Second)
		fmt.Printf(" .")
		time.Sleep(1 * time.Second)
		fmt.Printf(" .\n")
		if err := startup.Init(targetMac); err != nil {
			fmt.Println("Startup error:", err)
			return
		}
		fmt.Println("Local IP:  ", startup.LocalIP)
		fmt.Println("CIDR:      ", startup.CIDR)
		if startup.DeviceIP == "" {
			fmt.Println("Device not found on network")
		} else {
			fmt.Println("Device IP: ", startup.DeviceIP)
			break
		}
	}
	// startup check to confirm ip of device [END]



	msgCh := make(chan Message, 6)
	username := "root"
	password := "10011230"

	listeners := []*Listener{
	    NewListener(msgCh, targetMac, startup.DeviceIP, startup.ActiveInterface, username, password),
	}
	fmt.Printf("listeners created")

	for _, l := range listeners {
	    go l.Run()
	}

	fmt.Printf("listeners started")

	// graceful shutdown on SIGINT/SIGTERM
	sigs := make(chan os.Signal, 1)
	signal.Notify(sigs, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		nc, err := nats.Connect("nats://localhost:4222")
		if err != nil {
		    log.Fatal(err)
		}
		defer nc.Close()

		for {
			select {
			case msg := <-msgCh:
				subject := fmt.Sprintf("eventstream.%s", msg.Label)
				data, _ := json.Marshal(msg)

				if err := nc.Publish(subject, data); err != nil {
				    log.Fatal(err)
				}
			}
		}
	}()

	<-sigs
	fmt.Println("shutting down...")
	fmt.Println("done")
}


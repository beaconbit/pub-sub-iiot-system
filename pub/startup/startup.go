package startup

import (
	"fmt"
	"net"
	"os"
	"bytes"
	"bufio"
	"io"
	"os/exec"
	"runtime"
	"strings"
)

var (
	LocalIP  	string
	CIDR     	string
	DeviceIP 	string
	ActiveInterface string
)

// Init runs all network discovery steps
func Init(targetMac string) error {
	activeInterface, err := findActiveEthernetInterface()
	if err != nil {
		return fmt.Errorf("interface not found: %w", err)
	}

	ActiveInterface = activeInterface

	ip, cidr, err := getLocalNetwork()
	if err != nil {
		return fmt.Errorf("network not connected: %w", err)
	}

	LocalIP = ip
	CIDR = cidr

	ipFromMac, err := findIPFromMAC(targetMac)
	if err != nil {
		return fmt.Errorf("mac lookup failed: %w", err)
	}

	DeviceIP = ipFromMac
	return nil
}

// -------------------------------------------
// Internal (private) functions
// -------------------------------------------
func findActiveEthernetInterface() (string, error) {
    ifs, err := net.Interfaces()
    if err != nil {
        return "", err
    }

    for _, iface := range ifs {
        // Must be UP and RUNNING
        if iface.Flags&(net.FlagUp|net.FlagRunning) != (net.FlagUp | net.FlagRunning) {
            continue
        }

        // Skip loopback
        if iface.Flags&net.FlagLoopback != 0 {
            continue
        }

        // Filter only "wired" interface names: en*, eth*
        if !strings.HasPrefix(iface.Name, "en") && !strings.HasPrefix(iface.Name, "eth") {
            continue
        }

        // Check if it has an IPv4 address
        addrs, err := iface.Addrs()
        if err != nil {
            continue
        }

        for _, addr := range addrs {
            if ipnet, ok := addr.(*net.IPNet); ok && ipnet.IP.To4() != nil {
                return iface.Name, nil
            }
        }
    }

    return "", fmt.Errorf("no active ethernet interface found")
}


func getLocalNetwork() (string, string, error) {
	ifaces, err := net.Interfaces()
	if err != nil {
		return "", "", err
	}

	for _, iface := range ifaces {
		if iface.Flags&net.FlagUp == 0 || iface.Flags&net.FlagLoopback != 0 {
			continue
		}

		addrs, _ := iface.Addrs()
		for _, addr := range addrs {
			ipNet, ok := addr.(*net.IPNet)
			if !ok {
				continue
			}

			ip := ipNet.IP
			if ip == nil || ip.To4() == nil {
				continue
			}

			return ip.String(), ipNet.String(), nil
		}
	}

	return "", "", fmt.Errorf("no network connection found")
}

func findIPFromMAC(mac string) (string, error) {
	mac = strings.ToLower(strings.ReplaceAll(mac, "-", ":"))

	arpTable, err := readARPTable()
	if err != nil {
		return "", err
	}

	for ip, arpMac := range arpTable {
		if strings.ToLower(arpMac) == mac {
			return ip, nil
		}
	}

	return "", nil
}

func readARPTable() (map[string]string, error) {
    switch runtime.GOOS {
    case "linux":
        // Read ARP file directly, no exec needed
        data, err := os.ReadFile("/proc/net/arp")
        if err != nil {
            return nil, fmt.Errorf("failed to read /proc/net/arp: %w", err)
        }
        return parseArpOutput(bytes.NewReader(data))

    case "darwin", "windows":
        // For these systems, we still need the arp command
        cmd := exec.Command("arp", "-a")
        output, err := cmd.Output()
        if err != nil {
            return nil, fmt.Errorf("failed to run arp -a: %w", err)
        }
        return parseArpOutput(bytes.NewReader(output))

    default:
        return nil, fmt.Errorf("unsupported OS")
    }
}


func parseArpOutput(r io.Reader) (map[string]string, error) {
    scanner := bufio.NewScanner(r)
    results := map[string]string{}

    for scanner.Scan() {
        line := scanner.Text()
        fields := strings.Fields(line)
        if len(fields) < 3 {
            continue
        }

        // Linux (/proc/net/arp)
        if strings.Count(line, ":") == 5 && strings.Contains(line, ".") && len(fields) >= 4 {
            ip := fields[0]
            mac := fields[3]
            results[ip] = mac
            continue
        }

        // macOS / Windows (arp -a)
        if strings.Contains(line, "(") && strings.Contains(line, ")") && strings.Contains(line, " at ") {
            ip := line[strings.Index(line, "(")+1 : strings.Index(line, ")")]
            parts := strings.Split(line, " at ")
            if len(parts) < 2 {
                continue
            }
            afterAt := strings.Fields(parts[1])
            if len(afterAt) > 0 {
                results[ip] = afterAt[0]
            }
        }
    }

    return results, scanner.Err()
}



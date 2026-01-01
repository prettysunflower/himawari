package main

import (
	"fmt"
	"io"
	"net/http"
	"os"
	"os/signal"
	"regexp"
	"syscall"
	"time"

	"github.com/PuerkitoBio/goquery"

	"github.com/bwmarrin/discordgo"
)

type HpoiFigure struct {
	Name         string
	OriginalName string
	Price        string
	ReleaseDate  string
	Manufacturer string
	Scale        string
	Size         string
	MainImageURL string
}

var hpoiRegex = regexp.MustCompile(`https?://www\.hpoi\.net/hobby/\d+`)

func main() {
	session, err := discordgo.New("Bot " + os.Getenv("DISCORD_TOKEN"))

	if err != nil {
		panic(err)
	}

	session.AddHandler(messageReceived)
	session.Identify.Intents = discordgo.MakeIntent(discordgo.IntentsGuildMessages)

	err = session.Open()
	if err != nil {
		panic(err)
	}

	fmt.Println("Bot is now running.  Press CTRL-C to exit.")
	sc := make(chan os.Signal, 1)
	signal.Notify(sc, syscall.SIGINT, syscall.SIGTERM, os.Interrupt, os.Kill)
	<-sc

	_ = session.Close()
}

func processHPOI(hpoiURL string) (HpoiFigure, error) {
	hpoiPage, err := http.Get(hpoiURL)
	if err != nil {
		return HpoiFigure{}, err
	}
	htmlPage, err := goquery.NewDocumentFromReader(hpoiPage.Body)
	if err != nil {
		return HpoiFigure{}, err
	}

	var figure HpoiFigure

	htmlPage.Find(".hpoi-ibox-title > p").Each(func(i int, s *goquery.Selection) {
		title, _ := s.Attr("title")
		figure.Name = title
	})
	htmlPage.Find(".infoList-box > .hpoi-infoList-item").Each(func(i int, s *goquery.Selection) {
		key := s.ChildrenFiltered("span").Text()
		value := s.ChildrenFiltered("p").Text()

		switch key {
		case "名称":
			figure.OriginalName = value
		case "定价":
			figure.Price = value
		case "出货日":
			figure.ReleaseDate = value
		case "制作":
			figure.Manufacturer = value
		case "比例":
			figure.Scale = value
		case "尺寸":
			figure.Size = value
		}
	})
	htmlPage.Find(".isotope-img > img").Each(func(i int, s *goquery.Selection) {
		figure.MainImageURL, _ = s.Attr("src")
	})

	defer func(Body io.ReadCloser) {
		err := Body.Close()
		if err != nil {
			return
		}
	}(hpoiPage.Body)

	return figure, nil
}

func messageReceived(s *discordgo.Session, m *discordgo.MessageCreate) {
	if m.Author.ID == s.State.User.ID {
		// Message sent by bot, ignoring
		return
	}

	hpoiMatches := hpoiRegex.FindAllString(m.Content, -1)

	if len(hpoiMatches) > 0 {
		for _, hpoiURL := range hpoiMatches {
			figure, err := processHPOI(hpoiURL)
			if err != nil {
				fmt.Println(err)
				continue
			}

			embeddedFields := make([]*discordgo.MessageEmbedField, 0)

			if figure.OriginalName != "" {
				embeddedFields = append(embeddedFields, &discordgo.MessageEmbedField{
					Name:   "Original name",
					Value:  figure.OriginalName,
					Inline: false,
				})
			}
			if figure.Price != "" {
				embeddedFields = append(embeddedFields, &discordgo.MessageEmbedField{
					Name:   "Price",
					Value:  figure.Price,
					Inline: false,
				})
			}
			if figure.ReleaseDate != "" {
				embeddedFields = append(embeddedFields, &discordgo.MessageEmbedField{
					Name:   "Release Date",
					Value:  figure.ReleaseDate,
					Inline: false,
				})
			}
			if figure.Scale != "" {
				embeddedFields = append(embeddedFields, &discordgo.MessageEmbedField{
					Name:   "Scale",
					Value:  figure.Scale,
					Inline: false,
				})
			}
			if figure.Size != "" {
				embeddedFields = append(embeddedFields, &discordgo.MessageEmbedField{
					Name:   "Size",
					Value:  figure.Size,
					Inline: false,
				})
			}

			var embedImage discordgo.MessageEmbedImage

			if figure.MainImageURL != "" {
				embedImage = discordgo.MessageEmbedImage{
					URL: figure.MainImageURL,
				}
			}

			messageEmbed := discordgo.MessageEmbed{
				URL:         hpoiURL,
				Type:        discordgo.EmbedTypeRich,
				Title:       figure.Name,
				Description: "",
				Timestamp:   time.Now().Format(time.RFC3339),
				Color:       0,
				Footer:      nil,
				Image:       &embedImage,
				Thumbnail:   nil,
				Video:       nil,
				Provider:    nil,
				Author:      nil,
				Fields:      embeddedFields,
			}

			_, err = s.ChannelMessageSendEmbedReply(m.ChannelID, &messageEmbed, m.Reference())
			if err != nil {
				return
			}
		}
	}
}

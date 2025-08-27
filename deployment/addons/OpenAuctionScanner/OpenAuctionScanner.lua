OpenAuctionScanner = OpenAuctionScanner or {}
local OAS = OpenAuctionScanner

-- ============================================================================
-- CONSTANTS AND CONFIGURATION
-- ============================================================================
local VERSION = "1.0.1"

OAAData = OAAData or {}

-- Temporary storage during scanning
local TEMP_OAAData = {}

-- Print with green prefix
local oas_print = function(msg)
    print("|cFF00FF00[OAS]|r " .. msg)
end

-- Print with blue prefix
local oas_print_info = function(msg)
    print("|cFF0080FF[OAS]|r " .. msg)
end

-- Create the main frame for event handling
local oasFrame = CreateFrame("Frame", "OpenAuctionScannerFrame")

-- Item class names
local TARGET_CLASS_NAMES = {
    "weapon",
    "armor",
    "container",
    "consumable",
    "glyph",
    "trade goods",
    "projectile",
    "quiver",
    "recipe",
    "gem",
    "miscellaneous",
    "quest",
}

local MAX_ITEMS_PER_PAGE = 50

-- ============================================================================
-- GLOBAL STATE
-- ============================================================================
local state = {
    currentClassName = nil,
    currentClassNameIndex = 1,
    currentPage = 1,
    totalPages = 0,
    totalItems = 0,
    processedItems = 0,
    isProcessing = false,
    isDone = false,
    isDataCommitted = false,
}

local function ResetState()
    state = {
        currentClassName = nil,
        currentClassNameIndex = 1,
        currentPage = 1,
        totalPages = 0,
        totalItems = 0,
        processedItems = 0,
        isProcessing = false,
        isDone = false,
        isDataCommitted = false,
    }
end



-- ============================================================================
-- UI
-- ============================================================================
-- Create the status display frame
-- Initialize the addon
function OAS:Initialize()
    -- Create main frame with clean styling (taller and narrower)
    self.statusFrame = CreateFrame("Frame", "OpenAuctionScannerStatusFrame", UIParent)
    self.statusFrame:SetFrameStrata("FULLSCREEN_DIALOG")
    self.statusFrame:SetFrameLevel(9999)
    self.statusFrame:SetWidth(150)
    self.statusFrame:SetHeight(70)
    self.statusFrame:SetPoint("CENTER")
    self.statusFrame:SetMovable(true)
    self.statusFrame:EnableMouse(true)
    self.statusFrame:RegisterForDrag("LeftButton")
    self.statusFrame:SetScript("OnDragStart", self.statusFrame.StartMoving)
    self.statusFrame:SetScript("OnDragStop", self.statusFrame.StopMovingOrSizing)
    
    -- Create Atlas Browser style background
    self.statusFrame:SetBackdrop({
        bgFile = "Interface\\Buttons\\WHITE8x8",
        edgeFile = "Interface\\Tooltips\\UI-Tooltip-Border",
        tile = true,
        tileSize = 16,
        edgeSize = 2,
        insets = { left = 2, right = 2, top = 2, bottom = 2 }
    })
    self.statusFrame:SetBackdropColor(0.1, 0.15, 0.25, 0.95)
    self.statusFrame:SetBackdropBorderColor(0.4, 0.4, 0.6, 1)
    

    -- Title topbar
    self.titleTopbar = self.statusFrame:CreateTexture(nil, "BORDER")
    self.titleTopbar:SetPoint("TOP", self.statusFrame, "TOP", 0, 0)
    self.titleTopbar:SetWidth(150)
    self.titleTopbar:SetHeight(20)
    self.titleTopbar:SetTexture(0.4, 0.4, 0.6, 1)
    

    -- Create title text
    self.titleText = self.statusFrame:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    self.titleText:SetPoint("TOP", self.statusFrame, "TOP", 0, -5)
    self.titleText:SetText("OAS v" .. VERSION .. " @ " .. GetRealmName())
    self.titleText:SetTextColor(1, 1, 1)
    
    -- Create status text
    self.statusText = self.statusFrame:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
    self.statusText:SetPoint("TOP", self.titleText, "BOTTOM", 0, -20)
    self.statusText:SetText("OAS IDLE")
    self.statusText:SetTextColor(1, 1, 1)
    
    -- Create progress text
    self.progressText = self.statusFrame:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    self.progressText:SetPoint("TOP", self.statusText, "BOTTOM", 0, -10)
    self.progressText:SetText("")
    self.progressText:SetTextColor(0.8, 0.8, 0.8)
end

-- Update UI based on current state
function OAS:UpdateStatus()
    if not self.statusText then return end
    
    if state.isDataCommitted then
        self.statusText:SetText("OAS COMPLETED")
        self.statusText:SetTextColor(0, 1, 0) -- Green
    elseif state.isProcessing then
        self.statusText:SetText("OAS SCANNING")
        self.statusText:SetTextColor(1, 1, 0) -- Yellow
    else
        self.statusText:SetText("OAS IDLE")
        self.statusText:SetTextColor(1, 1, 1) -- White
    end
end






local function BuildClassNameToIndexMap()
    local classes = { GetAuctionItemClasses() }
    local map = {}
    for index, name in ipairs(classes) do
        if type(name) == "string" then
            map[string.lower(name)] = index
        end
    end
    return map
end

local function ResolveClassIndexByName(targetNameLower)
    if not targetNameLower then
        return nil
    end
    local map = BuildClassNameToIndexMap()
    if map[targetNameLower] then
        return map[targetNameLower]
    end
    -- fallback: substring match
    for nameLower, idx in pairs(map) do
        if string.find(nameLower, targetNameLower, 1, true) then
            return idx
        end
    end
    return nil
end



-- CORE QUERY FUNCTION
local function QueryAuctions(className, page)
    local classIndex = ResolveClassIndexByName(className)
    if not classIndex then
        oas_print("Invalid class name: " .. className)
        return
    end

    QueryAuctionItems("", nil, nil, nil, classIndex, nil, page, nil, nil, false)
end



-- PROCESSED HANDLER
local function OnProcessed(processedItems, numBatch, total)
    oas_print("Processing " .. processedItems .. " items from batch " .. numBatch .. " out of " .. total .. " total items")

    -- Set the total items
    state.totalItems = total
    -- Set the total pages (total / 50)
    state.totalPages = math.ceil(total / MAX_ITEMS_PER_PAGE)
    -- Increment the current page
    state.currentPage = state.currentPage + 1
    -- Increment the processed items
    state.processedItems = state.processedItems + processedItems
    -- Set the isProcessing flag to false
    state.isProcessing = false

    -- if current page is greater than or equal to total pages, set the done flag to true
    if state.currentPage >= state.totalPages then
        state.isDone = true
    end

    -- Print progress, make sure to check classname due to event order
    if (state.currentClassName) then
        oas_print_info("Progress: " .. state.processedItems .. " / " .. state.totalItems .. " items processed for class: " .. (state.currentClassName or "unknown"))
    end

    -- If we are not done, query the next page
    if not state.isDone then
        QueryAuctions(state.currentClassName, state.currentPage)
        return -- stop here
    end

    oas_print_info("State has changed to done, meaning we've finished the scan for the current class: " .. (state.currentClassName or "unknown"))
    -- We should now move on to the next class and reset the state.
    local maxClassNameIndex = #TARGET_CLASS_NAMES
    if state.currentClassNameIndex >= maxClassNameIndex then
        oas_print_info("Scanning complete, committing data to saved variables")
        
        -- Commit all collected data to saved variables
        for _, item in ipairs(TEMP_OAAData) do
            table.insert(OAAData, item)
        end
        oas_print_info("Committed " .. #TEMP_OAAData .. " total items to saved data")
        TEMP_OAAData = {} -- Clear temp table
        state.isDataCommitted = true
        OAS:UpdateStatus()

        return
    end

    -- Move on to the next class
    local nextClassNameIndex = state.currentClassNameIndex + 1
    ResetState() -- Reset the state for a clean slate

    -- Set the new state values, so next class name and then trigger the next query
    state.currentClassNameIndex = nextClassNameIndex
    state.currentClassName = TARGET_CLASS_NAMES[nextClassNameIndex]
    QueryAuctions(state.currentClassName, state.currentPage)
end


-- ON AUCTION ITEM LIST UPDATE
local function OnAuctionItemListUpdate()
    if state.isProcessing then
        return
    end

    -- Setup initial state
    local numBatch, total = GetNumAuctionItems("list")


    -- Process the event
    local processedItems = 0
    state.isProcessing = true
    OAS:UpdateStatus()
    for i = 1, (numBatch or 0) do
        local name, texture, count, quality, canUse, level, minBid, minIncrement, buyoutPrice, bidAmount, highestBidder, owner = GetAuctionItemInfo("list", i)

        -- Store the auction info data in a table
        if name then
            local link = GetAuctionItemLink("list", i)
            local itemId = nil
            local maxStack = nil
            local vendorPrice = nil
            
            if link then
                local idStr = string.match(link, "item:(%d+)")
                if idStr then 
                    itemId = tonumber(idStr)
                    local _, _, _, _, _, _, _, maxStackSize, _, _, vendorPriceValue = GetItemInfo(itemId)
                    maxStack = maxStackSize or 1  -- Default to 1 if nil
                    vendorPrice = vendorPriceValue or 0  -- Default to 0 if nil
                end
            end
            
            local realm = GetRealmName()

            -- We dont store canUse, highestBidder
            table.insert(TEMP_OAAData, {
                realm = realm,
                owner = owner,
                itemId = itemId,
                name = name,
                texture = texture,
                count = count,
                quality = quality,
                level = level,
                minBid = minBid,
                minIncrement = minIncrement,
                buyoutPrice = buyoutPrice,
                bidAmount = bidAmount,
                link = link,
                classIndex = state.currentClassNameIndex,
                className = state.currentClassName,
                maxStackSize = maxStack,
                vendorPrice = vendorPrice,
            })
        end

        processedItems = processedItems + 1
    end


    -- Listen for Update event to check whether we can query and are considered processed
    local frame = CreateFrame("Frame")
    frame:SetScript("OnUpdate", function(self, elapsed)
        local canQuery, canMassQuery = CanSendAuctionQuery("list")
        if canQuery then
            self:SetScript("OnUpdate", nil)
            OnProcessed(processedItems, numBatch, total)
        end
    end)


end


-- SCANNER
local function Scan()
    ResetState()
    OAS:UpdateStatus()

    local realm = GetRealmName()
    oas_print("Starting scan for realm: " .. realm)

    if not AuctionFrame or not AuctionFrame:IsShown() then
        oas_print("You must be at the Auction House to scan.")
        return
    end

    -- Always clear data when scanning again
    OAAData = {}
    TEMP_OAAData = {}

    -- Register event
    oasFrame:RegisterEvent("AUCTION_ITEM_LIST_UPDATE")
    -- Setup event handler
    oasFrame:SetScript("OnEvent", function(_, event)
        if event ~= "AUCTION_ITEM_LIST_UPDATE" then return end
        OnAuctionItemListUpdate()
    end)

    state.currentClassNameIndex = 6 -- Weapon is the first class
    state.currentClassName = TARGET_CLASS_NAMES[state.currentClassNameIndex]
    OAS:UpdateStatus()
    QueryAuctions(state.currentClassName, state.currentPage)
end


-- STOP
local function Stop()
    TEMP_OAAData = {}
    oasFrame:UnregisterEvent("AUCTION_ITEM_LIST_UPDATE")
    oasFrame:SetScript("OnEvent", nil)
    oasFrame:SetScript("OnUpdate", nil)

    oas_print("Scan stopped")
    ResetState()
    OAS:UpdateStatus()
end


-- Slash command handler
local function HandleSlashCommand(msg)
    local command = string.lower(msg or "")
    -- Log all class indexes
    if command == "info" then
        for name, index in pairs(TARGET_CLASS_NAMES) do
            oas_print("" .. name .. " = " .. index)
        end
    end

    if command == "scan" then
        Scan()
    end

    if command == "stop" then
        Stop()
    end
end


-- ============================================================================
-- INITIALIZATION
-- ============================================================================
SLASH_OPENAUCTIONSCANNER1 = "/oas"
SlashCmdList["OPENAUCTIONSCANNER"] = HandleSlashCommand

oas_print("OpenAuctionScanner v" .. VERSION .. " loaded. Use /oas scan to scan all categories; /oas stop to cancel.")

-- Initialize the addon
OAS:Initialize()